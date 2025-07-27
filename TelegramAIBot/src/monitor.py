"""
System Monitor - Tracks performance and resource usage
Monitors CPU, GPU, memory usage and system health
"""

import asyncio
import logging
import psutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitors system resources and performance"""
    
    def __init__(self):
        self.is_running = False
        self.stats_history = []
        self.max_history_size = 1000
        self.monitoring_interval = 30  # seconds
        self.alerts = []
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'gpu_memory_percent': 85
        }
        
    async def start(self):
        """Start system monitoring"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("System monitor started")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
    async def stop(self):
        """Stop system monitoring"""
        self.is_running = False
        logger.info("System monitor stopped")
        
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get current system statistics
        
        Returns:
            Dictionary with system stats
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory usage
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # GPU stats (if available)
            gpu_stats = await self._get_gpu_stats()
            
            # Tool availability
            tools_status = await self._check_tools_availability()
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': round(cpu_percent, 1),
                'cpu_count': cpu_count,
                'cpu_freq_mhz': round(cpu_freq.current, 1) if cpu_freq else 0,
                'memory_percent': round(memory.percent, 1),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'swap_percent': round(swap.percent, 1),
                'disk_percent': round(disk.percent, 1),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'tools': tools_status
            }
            
            # Add GPU stats if available
            if gpu_stats:
                stats.update(gpu_stats)
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'tools': {'ffmpeg': False, 'realesrgan': False, 'gpu': False}
            }
            
    async def _get_gpu_stats(self) -> Optional[Dict[str, Any]]:
        """Get GPU statistics using nvidia-smi"""
        try:
            # Try to get NVIDIA GPU stats
            cmd = [
                'nvidia-smi',
                '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw',
                '--format=csv,noheader,nounits'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode().strip()
                lines = output.split('\n')
                
                gpus = []
                for i, line in enumerate(lines):
                    parts = line.split(', ')
                    if len(parts) >= 5:
                        gpu_util, mem_used, mem_total, temp, power = parts
                        
                        try:
                            gpus.append({
                                'id': i,
                                'utilization_percent': float(gpu_util),
                                'memory_used_mb': float(mem_used),
                                'memory_total_mb': float(mem_total),
                                'memory_percent': round((float(mem_used) / float(mem_total)) * 100, 1),
                                'temperature_c': float(temp),
                                'power_draw_w': float(power)
                            })
                        except ValueError:
                            continue
                            
                if gpus:
                    # Return stats for first GPU (most common case)
                    primary_gpu = gpus[0]
                    return {
                        'gpu_count': len(gpus),
                        'gpu_percent': primary_gpu['utilization_percent'],
                        'gpu_memory_percent': primary_gpu['memory_percent'],
                        'gpu_memory_used_mb': primary_gpu['memory_used_mb'],
                        'gpu_memory_total_mb': primary_gpu['memory_total_mb'],
                        'gpu_temperature_c': primary_gpu['temperature_c'],
                        'gpu_power_w': primary_gpu['power_draw_w'],
                        'all_gpus': gpus
                    }
                    
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
            
        return None
        
    async def _check_tools_availability(self) -> Dict[str, bool]:
        """Check availability of processing tools"""
        tools_status = {}
        
        # Check FFmpeg
        try:
            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            tools_status['ffmpeg'] = process.returncode == 0
        except FileNotFoundError:
            tools_status['ffmpeg'] = False
            
        # Check Real-ESRGAN
        try:
            # Check for common Real-ESRGAN executables
            realesrgan_names = ['realesrgan-ncnn-vulkan', 'Real-ESRGAN', 'realesrgan']
            tools_status['realesrgan'] = False
            
            for exe_name in realesrgan_names:
                try:
                    process = await asyncio.create_subprocess_exec(
                        exe_name, '-h',
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    if process.returncode == 0:
                        tools_status['realesrgan'] = True
                        break
                except FileNotFoundError:
                    continue
        except Exception:
            tools_status['realesrgan'] = False
            
        # Check GPU availability
        try:
            process = await asyncio.create_subprocess_exec(
                'nvidia-smi',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            tools_status['gpu'] = process.returncode == 0
        except FileNotFoundError:
            tools_status['gpu'] = False
            
        # Check Video2X
        try:
            process = await asyncio.create_subprocess_exec(
                'video2x', '--help',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            tools_status['video2x'] = process.returncode == 0
        except FileNotFoundError:
            tools_status['video2x'] = False
            
        return tools_status
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Get current stats
                stats = await self.get_system_stats()
                
                # Add to history
                self.stats_history.append(stats)
                
                # Limit history size
                if len(self.stats_history) > self.max_history_size:
                    self.stats_history.pop(0)
                    
                # Check for alerts
                await self._check_alerts(stats)
                
                # Log high resource usage
                if stats.get('cpu_percent', 0) > 90:
                    logger.warning(f"High CPU usage: {stats['cpu_percent']}%")
                if stats.get('memory_percent', 0) > 90:
                    logger.warning(f"High memory usage: {stats['memory_percent']}%")
                if stats.get('disk_percent', 0) > 95:
                    logger.error(f"Critical disk usage: {stats['disk_percent']}%")
                    
                # Wait for next iteration
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
                
    async def _check_alerts(self, stats: Dict[str, Any]):
        """Check for alert conditions"""
        current_time = datetime.now()
        
        # Check CPU threshold
        if stats.get('cpu_percent', 0) > self.thresholds['cpu_percent']:
            self._add_alert('high_cpu', f"CPU usage: {stats['cpu_percent']}%", current_time)
            
        # Check memory threshold
        if stats.get('memory_percent', 0) > self.thresholds['memory_percent']:
            self._add_alert('high_memory', f"Memory usage: {stats['memory_percent']}%", current_time)
            
        # Check disk threshold
        if stats.get('disk_percent', 0) > self.thresholds['disk_percent']:
            self._add_alert('high_disk', f"Disk usage: {stats['disk_percent']}%", current_time)
            
        # Check GPU memory if available
        if stats.get('gpu_memory_percent', 0) > self.thresholds['gpu_memory_percent']:
            self._add_alert('high_gpu_memory', f"GPU memory: {stats['gpu_memory_percent']}%", current_time)
            
    def _add_alert(self, alert_type: str, message: str, timestamp: datetime):
        """Add alert to alerts list"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': timestamp.isoformat(),
            'resolved': False
        }
        
        # Check if similar alert already exists in last 10 minutes
        recent_alerts = [
            a for a in self.alerts
            if a['type'] == alert_type and
            datetime.fromisoformat(a['timestamp']) > timestamp - timedelta(minutes=10)
        ]
        
        if not recent_alerts:
            self.alerts.append(alert)
            logger.warning(f"System alert: {alert_type} - {message}")
            
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
            
    async def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate performance report for specified time period
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            Performance report dictionary
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter stats within time period
            recent_stats = [
                stat for stat in self.stats_history
                if datetime.fromisoformat(stat['timestamp']) > cutoff_time
            ]
            
            if not recent_stats:
                return {'error': 'No data available for the specified period'}
                
            # Calculate averages and peaks
            cpu_values = [s.get('cpu_percent', 0) for s in recent_stats]
            memory_values = [s.get('memory_percent', 0) for s in recent_stats]
            disk_values = [s.get('disk_percent', 0) for s in recent_stats]
            
            report = {
                'period_hours': hours,
                'data_points': len(recent_stats),
                'cpu': {
                    'average': round(sum(cpu_values) / len(cpu_values), 1),
                    'peak': max(cpu_values),
                    'minimum': min(cpu_values)
                },
                'memory': {
                    'average': round(sum(memory_values) / len(memory_values), 1),
                    'peak': max(memory_values),
                    'minimum': min(memory_values)
                },
                'disk': {
                    'average': round(sum(disk_values) / len(disk_values), 1),
                    'peak': max(disk_values),
                    'minimum': min(disk_values)
                },
                'alerts_count': len([
                    a for a in self.alerts
                    if datetime.fromisoformat(a['timestamp']) > cutoff_time
                ]),
                'generated_at': datetime.now().isoformat()
            }
            
            # Add GPU stats if available
            gpu_values = [s.get('gpu_percent', 0) for s in recent_stats if 'gpu_percent' in s]
            if gpu_values:
                report['gpu'] = {
                    'average': round(sum(gpu_values) / len(gpu_values), 1),
                    'peak': max(gpu_values),
                    'minimum': min(gpu_values)
                }
                
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
            
    async def cleanup_old_data(self, days: int = 7):
        """Clean up old monitoring data"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # Clean stats history
        self.stats_history = [
            stat for stat in self.stats_history
            if datetime.fromisoformat(stat['timestamp']) > cutoff_time
        ]
        
        # Clean alerts
        self.alerts = [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert['timestamp']) > cutoff_time
        ]
        
        logger.info(f"Cleaned monitoring data older than {days} days")
        
    def get_current_alerts(self) -> List[Dict[str, Any]]:
        """Get current unresolved alerts"""
        return [alert for alert in self.alerts if not alert.get('resolved', False)]
        
    async def test_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health test"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'tests': {}
        }
        
        try:
            # Test system resources
            stats = await self.get_system_stats()
            
            # CPU test
            if stats.get('cpu_percent', 0) > 90:
                health_report['tests']['cpu'] = {'status': 'critical', 'message': 'High CPU usage'}
                health_report['overall_status'] = 'critical'
            elif stats.get('cpu_percent', 0) > 70:
                health_report['tests']['cpu'] = {'status': 'warning', 'message': 'Elevated CPU usage'}
                if health_report['overall_status'] == 'healthy':
                    health_report['overall_status'] = 'warning'
            else:
                health_report['tests']['cpu'] = {'status': 'healthy', 'message': 'CPU usage normal'}
                
            # Memory test
            if stats.get('memory_percent', 0) > 90:
                health_report['tests']['memory'] = {'status': 'critical', 'message': 'High memory usage'}
                health_report['overall_status'] = 'critical'
            elif stats.get('memory_percent', 0) > 80:
                health_report['tests']['memory'] = {'status': 'warning', 'message': 'Elevated memory usage'}
                if health_report['overall_status'] == 'healthy':
                    health_report['overall_status'] = 'warning'
            else:
                health_report['tests']['memory'] = {'status': 'healthy', 'message': 'Memory usage normal'}
                
            # Disk test
            if stats.get('disk_percent', 0) > 95:
                health_report['tests']['disk'] = {'status': 'critical', 'message': 'Critical disk usage'}
                health_report['overall_status'] = 'critical'
            elif stats.get('disk_percent', 0) > 85:
                health_report['tests']['disk'] = {'status': 'warning', 'message': 'High disk usage'}
                if health_report['overall_status'] == 'healthy':
                    health_report['overall_status'] = 'warning'
            else:
                health_report['tests']['disk'] = {'status': 'healthy', 'message': 'Disk usage normal'}
                
            # Tools availability test
            tools = stats.get('tools', {})
            if not tools.get('ffmpeg', False):
                health_report['tests']['ffmpeg'] = {'status': 'critical', 'message': 'FFmpeg not available'}
                health_report['overall_status'] = 'critical'
            else:
                health_report['tests']['ffmpeg'] = {'status': 'healthy', 'message': 'FFmpeg available'}
                
            if not tools.get('realesrgan', False):
                health_report['tests']['realesrgan'] = {'status': 'warning', 'message': 'Real-ESRGAN not available'}
                if health_report['overall_status'] == 'healthy':
                    health_report['overall_status'] = 'warning'
            else:
                health_report['tests']['realesrgan'] = {'status': 'healthy', 'message': 'Real-ESRGAN available'}
                
            return health_report
            
        except Exception as e:
            logger.error(f"Error in system health test: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'error',
                'error': str(e)
            }
    
    async def get_system_stats(self):
        """Get basic system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_free_gb': memory.free / (1024**3),
                'memory_total_gb': memory.total / (1024**3),
                'disk_used_gb': disk.used / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'disk_percent': (disk.used / disk.total) * 100
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_used_gb': 0,
                'memory_free_gb': 0,
                'memory_total_gb': 0,
                'disk_used_gb': 0,
                'disk_free_gb': 0,
                'disk_total_gb': 0,
                'disk_percent': 0
            }
    
    async def get_detailed_stats(self):
        """Get detailed system statistics"""
        try:
            basic_stats = await self.get_system_stats()
            
            # CPU info
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            
            # Network info  
            network = psutil.net_io_counters()
            
            detailed = basic_stats.copy()
            detailed.update({
                'cpu_cores': cpu_count,
                'cpu_freq': cpu_freq.current if cpu_freq else 'غير متاح',
                'cpu_avg_5min': basic_stats['cpu_percent'],  # Simplified
                'memory_cached_gb': (psutil.virtual_memory().cached if hasattr(psutil.virtual_memory(), 'cached') else 0) / (1024**3),
                'network_sent_mb': network.bytes_sent / (1024**2),
                'network_recv_mb': network.bytes_recv / (1024**2),
                'disk_read_speed': 'غير متاح',
                'disk_write_speed': 'غير متاح',
                'upload_speed': 'غير متاح',
                'download_speed': 'غير متاح'
            })
            
            return detailed
            
        except Exception as e:
            logger.error(f"Error getting detailed stats: {e}")
            return await self.get_system_stats()
