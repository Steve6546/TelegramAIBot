#!/usr/bin/env python3
"""
Smart Media AI Assistant - Main Entry Point
Telegram bot with AI agent integration for intelligent video/audio enhancement
"""

import asyncio
import logging
import os
import json
from pathlib import Path

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from src.bot_handlers import BotHandlers
from src.smart_ai_agent import SmartAIAgent
from src.tool_manager import ToolManager
from src.storage import StorageManager
from src.task_queue import TaskQueue
from src.monitor import SystemMonitor

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SmartMediaBot:
    """Main bot class that orchestrates all components"""
    
    def __init__(self):
        self.config = self.load_config()
        self.storage = StorageManager()
        self.task_queue = TaskQueue()
        self.tool_manager = ToolManager()
        self.ai_agent = SmartAIAgent(self.tool_manager)
        self.monitor = SystemMonitor()
        self.bot_handlers = BotHandlers(
            self.ai_agent,
            self.task_queue,
            self.storage,
            self.monitor
        )
        
    def load_config(self):
        """Load configuration from file or environment variables"""
        config_path = Path("config.json")
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
            
        # Environment variables override config file
        config['telegram_token'] = os.getenv('TELEGRAM_BOT_TOKEN', config.get('telegram_token'))
        config['openai_api_key'] = os.getenv('OPENAI_API_KEY', config.get('openai_api_key'))
        config['admin_users'] = config.get('admin_users', [])
        config['max_file_size'] = config.get('max_file_size', 50 * 1024 * 1024)  # 50MB
        config['max_concurrent_tasks'] = config.get('max_concurrent_tasks', 3)
        
        if not config['telegram_token']:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment or config file")
        if not config.get('openai_api_key') and not os.getenv('GOOGLE_API_KEY'):
            raise ValueError("Either OPENAI_API_KEY or GOOGLE_API_KEY must be provided")
            
        return config
        
    async def setup_directories(self):
        """Ensure all required directories exist"""
        directories = ['downloads', 'temp', 'media', 'logs']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            
    async def start_bot(self):
        """Initialize and start the Telegram bot"""
        logger.info("Starting Smart Media AI Assistant Bot...")
        
        # Setup directories
        await self.setup_directories()
        
        # Initialize components
        await self.task_queue.start()
        await self.monitor.start()
        
        # Create application
        application = Application.builder().token(self.config['telegram_token']).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.bot_handlers.start_command))
        application.add_handler(CommandHandler("help", self.bot_handlers.help_command))
        application.add_handler(CommandHandler("status", self.bot_handlers.status_command))
        application.add_handler(CommandHandler("cancel", self.bot_handlers.cancel_command))
        
        # Message handlers
        application.add_handler(MessageHandler(
            filters.VIDEO | filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE,
            self.bot_handlers.handle_media
        ))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handlers.handle_text))
        
        # Callback handlers for inline buttons
        application.add_handler(CallbackQueryHandler(self.bot_handlers.handle_callback))
        
        # Error handler
        application.add_error_handler(self.bot_handlers.error_handler)
        
        logger.info("Bot initialized successfully. Starting polling...")
        
        # Start the bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        try:
            # Keep the bot running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            await self.cleanup()
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            
    async def cleanup(self):
        """Cleanup resources on shutdown"""
        logger.info("Cleaning up resources...")
        await self.task_queue.stop()
        await self.monitor.stop()
        self.storage.cleanup_temp_files()

def main():
    """Main entry point"""
    try:
        bot = SmartMediaBot()
        asyncio.run(bot.start_bot())
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()
