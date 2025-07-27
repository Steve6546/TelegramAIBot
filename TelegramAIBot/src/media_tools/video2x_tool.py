"""
Video2X Tool - Alternative video upscaling solution
Provides fallback video enhancement when Real-ESRGAN is not available
"""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Video2XTool:
    """Video2X wrapper for video upscaling and enhancement"""
    
    def __init__(self):
        self.video2x_path = self._find_video2x_executable()
        self.temp_dir = Path("temp/video2x")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def _find_video2x_executable(self) -> Optional[str]:
        """Find Video2X executable in system PATH or common locations"""
        # Check if video2x is in PATH
        if shutil.which('video2x'):
            return 'video2x'
            
        # Check common installation paths
        common_paths = [
            '/usr/local/bin/video2x',
            '/opt/video2x/video2x',
            './video2x/video2x',
            './video2x'
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
                
        return None
        
    async def is_available(self) -> bool:
        """Check if Video2X is available"""
        if not self.video2x_path:
            return False
            
        try:
            # Test if Video2X runs
            process = await asyncio.create_subprocess_exec(
                self.video2x_path, '--help',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except (FileNotFoundError, PermissionError):
            return False
            
    async def upscale(self, file_path: str, resolution: str) -> str:
        """
        Upscale video using Video2X
        
        Args:
            file_path: Path to input video
            resolution: Target resolution ('2k', '4k', '1080p', '720p')
            
        Returns:
            Path to upscaled video
        """
        try:
            if not await self.is_available():
                raise RuntimeError("Video2X not available")
                
            # Get scale factor and target dimensions
            scale_factor = self._get_scale_factor(resolution)
            width, height = self._get_resolution_dimensions(resolution)
            
            # Generate output path
            output_path = self._generate_output_path(file_path, f"video2x_{resolution}")
            
            # Prepare Video2X command
            cmd = [
                self.video2x_path,
                '-i', file_path,
                '-o', output_path,
                '--width', str(width),
                '--height', str(height),
                '--driver', 'waifu2x_caffe',  # Default driver
                '--processes', '1'  # Limit processes to avoid overload
            ]
            
            # Add GPU acceleration if available
            if await self._has_gpu_support():
                cmd.extend(['--gpu', '0'])
                
            logger.info(f"Running Video2X: {' '.join(cmd)}")
            
            # Run Video2X with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=3600  # 1 hour timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise RuntimeError("Video2X processing timed out")
                
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Video2X failed: {error_msg}")
                
            logger.info("Video2X upscaling completed successfully")
            return output_path
            
        except Exception as e:
            logger.error(f"Error upscaling with Video2X: {e}")
            raise
            
    async def enhance_with_filters(self, file_path: str, filters: list) -> str:
        """
        Apply enhancement filters using Video2X
        
        Args:
            file_path: Path to input video
            filters: List of filter names to apply
            
        Returns:
            Path to enhanced video
        """
        try:
            if not await self.is_available():
                raise RuntimeError("Video2X not available")
                
            output_path = self._generate_output_path(file_path, "enhanced")
            
            # Basic enhancement command
            cmd = [
                self.video2x_path,
                '-i', file_path,
                '-o', output_path,
                '--driver', 'anime4kcpp',  # Good for general enhancement
                '--scale', '1.5',  # Slight upscale with enhancement
                '--processes', '1'
            ]
            
            # Add specific filters
            for filter_name in filters:
                if filter_name == 'denoise':
                    cmd.extend(['--denoise', '3'])
                elif filter_name == 'sharpen':
                    cmd.extend(['--sharpen', '0.3'])
                elif filter_name == 'fast':
                    cmd.extend(['--fast'])
                    
            if await self._has_gpu_support():
                cmd.extend(['--gpu', '0'])
                
            logger.info(f"Running Video2X enhancement: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Video2X enhancement failed: {error_msg}")
                
            return output_path
            
        except Exception as e:
            logger.error(f"Error enhancing with Video2X: {e}")
            raise
            
    async def _has_gpu_support(self) -> bool:
        """Check if GPU acceleration is available for Video2X"""
        try:
            # Check for NVIDIA GPU
            process = await asyncio.create_subprocess_exec(
                'nvidia-smi',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False
            
    def _get_scale_factor(self, resolution: str) -> float:
        """Get appropriate scale factor for target resolution"""
        resolution_map = {
            '720p': 1.0,
            '1080p': 1.5,
            '2k': 2.0,
            '4k': 2.5
        }
        return resolution_map.get(resolution.lower(), 2.0)
        
    def _get_resolution_dimensions(self, resolution: str) -> tuple:
        """Get width and height for resolution string"""
        resolution_map = {
            '720p': (1280, 720),
            '1080p': (1920, 1080),
            '2k': (2560, 1440),
            '4k': (3840, 2160)
        }
        return resolution_map.get(resolution.lower(), (1920, 1080))
        
    def _generate_output_path(self, input_path: str, suffix: str) -> str:
        """Generate output file path"""
        input_path = Path(input_path)
        output_dir = Path("media")
        output_dir.mkdir(exist_ok=True)
        
        output_name = f"{input_path.stem}_{suffix}{input_path.suffix}"
        return str(output_dir / output_name)
        
    async def batch_upscale(self, file_paths: list, resolution: str) -> list:
        """
        Upscale multiple videos in batch
        
        Args:
            file_paths: List of input video paths
            resolution: Target resolution
            
        Returns:
            List of output file paths
        """
        try:
            if not await self.is_available():
                raise RuntimeError("Video2X not available")
                
            results = []
            
            for file_path in file_paths:
                try:
                    output_path = await self.upscale(file_path, resolution)
                    results.append(output_path)
                    logger.info(f"Successfully upscaled {file_path} to {output_path}")
                except Exception as e:
                    logger.error(f"Failed to upscale {file_path}: {e}")
                    results.append(None)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error in batch upscaling: {e}")
            raise
            
    async def get_supported_formats(self) -> list:
        """Get list of supported input/output formats"""
        return [
            'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv',
            'webm', 'm4v', '3gp', 'ts', 'mts'
        ]
        
    async def estimate_processing_time(self, file_path: str, resolution: str) -> int:
        """
        Estimate processing time for Video2X upscaling
        
        Args:
            file_path: Path to input file
            resolution: Target resolution
            
        Returns:
            Estimated time in seconds
        """
        try:
            # Get file info using ffprobe
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                data = json.loads(stdout.decode())
                duration = float(data.get('format', {}).get('duration', 60))
                
                # Estimate based on resolution and duration
                scale_factor = self._get_scale_factor(resolution)
                base_time = duration * scale_factor * 10  # Rough estimate
                
                # Adjust for GPU availability
                if await self._has_gpu_support():
                    base_time *= 0.3
                    
                return max(int(base_time), 30)  # Minimum 30 seconds
            else:
                return 300  # Default 5 minutes
                
        except Exception as e:
            logger.error(f"Error estimating processing time: {e}")
            return 300
