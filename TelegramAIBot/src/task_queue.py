"""
Task Queue Manager - Handles background processing tasks
Manages task execution, progress tracking, and user notifications
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """Task data structure"""
    id: str
    user_id: int
    task_type: str
    file_id: str
    parameters: Dict[str, Any]
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    chat_id: Optional[int] = None
    message_id: Optional[int] = None
    estimated_duration: int = 60  # seconds

class TaskQueue:
    """Manages background task processing and execution"""
    
    def __init__(self, max_concurrent_tasks: int = 3):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: List[str] = []
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.is_running = False
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'cancelled': 0
        }
        
    async def start(self):
        """Start the task queue processor"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("Task queue started")
        
        # Start the main processing loop
        asyncio.create_task(self._process_queue())
        
    async def stop(self):
        """Stop the task queue and cancel all running tasks"""
        self.is_running = False
        
        # Cancel all running tasks
        for task_id, task_coroutine in self.running_tasks.items():
            task_coroutine.cancel()
            task = self.tasks.get(task_id)
            if task:
                task.status = TaskStatus.CANCELLED
                
        # Wait for tasks to complete cancellation
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
            
        logger.info("Task queue stopped")
        
    async def add_task(
        self,
        user_id: int,
        task_type: str,
        file_id: str,
        parameters: Dict[str, Any],
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> str:
        """
        Add a new task to the queue
        
        Args:
            user_id: User ID
            task_type: Type of task (enhance, convert, etc.)
            file_id: Telegram file ID or local file path
            parameters: Task parameters
            chat_id: Chat ID for notifications
            message_id: Message ID for updates
            
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            user_id=user_id,
            task_type=task_type,
            file_id=file_id,
            parameters=parameters,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            chat_id=chat_id,
            message_id=message_id
        )
        
        self.tasks[task_id] = task
        self.pending_queue.append(task_id)
        
        logger.info(f"Added task {task_id} for user {user_id}: {task_type}")
        
        return task_id
        
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)
        
    async def get_user_tasks(self, user_id: int, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks for a user, optionally filtered by status"""
        user_tasks = [
            task for task in self.tasks.values()
            if task.user_id == user_id
        ]
        
        if status:
            user_tasks = [task for task in user_tasks if task.status == status]
            
        return sorted(user_tasks, key=lambda t: t.created_at, reverse=True)
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        if task.status == TaskStatus.PENDING:
            # Remove from pending queue
            if task_id in self.pending_queue:
                self.pending_queue.remove(task_id)
            task.status = TaskStatus.CANCELLED
            self.stats['cancelled'] += 1
            return True
            
        elif task.status == TaskStatus.RUNNING:
            # Cancel running task
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                task.status = TaskStatus.CANCELLED
                self.stats['cancelled'] += 1
                return True
                
        return False
        
    async def cancel_user_tasks(self, user_id: int) -> int:
        """Cancel all tasks for a user"""
        user_tasks = await self.get_user_tasks(user_id)
        cancelled_count = 0
        
        for task in user_tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                if await self.cancel_task(task.id):
                    cancelled_count += 1
                    
        return cancelled_count
        
    async def update_progress(self, task_id: str, progress: float, message: Optional[str] = None):
        """Update task progress"""
        task = self.tasks.get(task_id)
        if task:
            task.progress = max(0.0, min(100.0, progress))
            if message:
                # Could store progress messages if needed
                pass
                
    async def get_queue_info(self) -> Dict[str, Any]:
        """Get queue statistics and information"""
        pending_count = len(self.pending_queue)
        running_count = len(self.running_tasks)
        
        # Count completed tasks in last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        completed_today = len([
            task for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED and
            task.completed_at and task.completed_at > yesterday
        ])
        
        return {
            'pending_tasks': pending_count,
            'active_tasks': running_count,
            'completed_today': completed_today,
            'total_stats': self.stats.copy(),
            'queue_capacity': self.max_concurrent_tasks
        }
        
    async def _process_queue(self):
        """Main queue processing loop"""
        while self.is_running:
            try:
                # Check if we can start new tasks
                if len(self.running_tasks) < self.max_concurrent_tasks and self.pending_queue:
                    task_id = self.pending_queue.pop(0)
                    task = self.tasks.get(task_id)
                    
                    if task and task.status == TaskStatus.PENDING:
                        # Start processing the task
                        task_coroutine = asyncio.create_task(self._execute_task(task))
                        self.running_tasks[task_id] = task_coroutine
                        
                # Clean up completed tasks
                completed_tasks = [
                    task_id for task_id, task_coroutine in self.running_tasks.items()
                    if task_coroutine.done()
                ]
                
                for task_id in completed_tasks:
                    del self.running_tasks[task_id]
                    
                # Wait before next iteration
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}")
                await asyncio.sleep(5)
                
    async def _execute_task(self, task: Task):
        """Execute a single task"""
        try:
            async with self.task_semaphore:
                logger.info(f"Starting task {task.id}: {task.task_type}")
                
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                
                # Import here to avoid circular imports
                from .tool_manager import ToolManager
                from .storage import StorageManager
                
                tool_manager = ToolManager()
                storage_manager = StorageManager()
                
                # Get input file path
                if task.file_id.startswith('/') or task.file_id.startswith('.'):
                    # It's already a file path
                    input_path = task.file_id
                else:
                    # It's a Telegram file ID - would need to download first
                    # This is a simplified version
                    input_path = task.file_id
                
                # Execute based on task type
                if task.task_type == "enhance":
                    result_path = await tool_manager.enhance_video(input_path, task.parameters)
                elif task.task_type == "convert":
                    result_path = await tool_manager.convert_format(input_path, task.parameters)
                elif task.task_type == "ai_enhance":
                    # AI-powered enhancement
                    analysis = await tool_manager.analyze_media(input_path)
                    # Based on analysis, choose best enhancement
                    enhanced_params = self._determine_ai_enhancement(analysis, task.parameters)
                    result_path = await tool_manager.enhance_video(input_path, enhanced_params)
                else:
                    raise ValueError(f"Unknown task type: {task.task_type}")
                
                # Move result to media directory
                final_path = storage_manager.move_to_media(
                    result_path,
                    f"processed_{task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                )
                
                # Mark task as completed
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.progress = 100.0
                task.result_path = final_path
                
                self.stats['successful'] += 1
                self.stats['total_processed'] += 1
                
                # Send notification to user
                await self._notify_task_completion(task)
                
                logger.info(f"Task {task.id} completed successfully")
                
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"Task {task.id} was cancelled")
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error_message = str(e)
            
            self.stats['failed'] += 1
            self.stats['total_processed'] += 1
            
            # Send error notification
            await self._notify_task_error(task)
            
    def _determine_ai_enhancement(self, analysis: Dict, parameters: Dict) -> Dict:
        """Determine best enhancement parameters based on AI analysis"""
        enhanced_params = parameters.copy()
        
        # Simple logic to determine enhancement based on file analysis
        video_info = analysis.get('video', {})
        width = video_info.get('width', 0)
        height = video_info.get('height', 0)
        
        if width < 1280 or height < 720:
            # Low resolution - upscale to 1080p
            enhanced_params['type'] = 'upscale_1080p'
        elif width < 1920 or height < 1080:
            # Medium resolution - upscale to 2K
            enhanced_params['type'] = 'upscale_2k'
        else:
            # High resolution - just enhance quality
            enhanced_params['type'] = 'enhance'
            
        return enhanced_params
        
    async def _notify_task_completion(self, task: Task):
        """Send completion notification to user"""
        try:
            if task.chat_id:
                # Import here to avoid circular dependency
                from telegram import Bot
                import os
                
                bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
                
                message = f"""
✅ *تم إنجاز المعالجة بنجاح!*

معرف المهمة: `{task.id}`
نوع المعالجة: {task.task_type}
وقت المعالجة: {self._format_duration(task)}
                """
                
                # Send the result file
                if task.result_path and Path(task.result_path).exists():
                    await bot.send_document(
                        chat_id=task.chat_id,
                        document=open(task.result_path, 'rb'),
                        caption=message,
                        parse_mode='Markdown'
                    )
                else:
                    await bot.send_message(
                        chat_id=task.chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
        except Exception as e:
            logger.error(f"Error sending completion notification: {e}")
            
    async def _notify_task_error(self, task: Task):
        """Send error notification to user"""
        try:
            if task.chat_id:
                from telegram import Bot
                import os
                
                bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
                
                message = f"""
❌ *فشل في معالجة الملف*

معرف المهمة: `{task.id}`
نوع المعالجة: {task.task_type}
سبب الفشل: {task.error_message or 'خطأ غير معروف'}

يرجى المحاولة مرة أخرى أو التواصل مع الدعم.
                """
                
                await bot.send_message(
                    chat_id=task.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            
    def _format_duration(self, task: Task) -> str:
        """Format task duration for display"""
        if not task.started_at or not task.completed_at:
            return "غير معروف"
            
        duration = task.completed_at - task.started_at
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds} ثانية"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes} دقيقة و {seconds} ثانية"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours} ساعة و {minutes} دقيقة"
            
    async def cleanup_old_tasks(self, max_age_days: int = 7):
        """Clean up old completed/failed tasks"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        tasks_to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            and task.completed_at and task.completed_at < cutoff_date
        ]
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            
        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
        return len(tasks_to_remove)
    
    async def get_active_tasks_count(self):
        """Get count of active tasks"""
        return len([task for task in self.tasks.values() if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]])
    
    async def get_completed_tasks_count(self):
        """Get count of completed tasks"""
        return len([task for task in self.tasks.values() if task.status == TaskStatus.COMPLETED])
