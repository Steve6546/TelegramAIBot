"""
Tool Manager - Orchestrates media processing tools
Manages FFmpeg, Real-ESRGAN, and other enhancement tools
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .media_tools.ffmpeg_tool import FFmpegTool
from .media_tools.realesrgan_tool import RealESRGANTool
from .media_tools.video2x_tool import Video2XTool

logger = logging.getLogger(__name__)

class ToolManager:
    """Manages and orchestrates all media processing tools"""
    
    def __init__(self):
        self.ffmpeg = FFmpegTool()
        self.realesrgan = RealESRGANTool()
        self.video2x = Video2XTool()
        self.available_tools = {}
        
        # Check tool availability on initialization
        asyncio.create_task(self.check_tool_availability())
        
    async def check_tool_availability(self):
        """Check which tools are available on the system"""
        self.available_tools = {
            'ffmpeg': await self.ffmpeg.is_available(),
            'realesrgan': await self.realesrgan.is_available(),
            'video2x': await self.video2x.is_available(),
            'gpu': await self.check_gpu_availability()
        }
        
        logger.info(f"Tool availability: {self.available_tools}")
        
    async def check_gpu_availability(self) -> bool:
        """Check if GPU acceleration is available"""
        try:
            # Check for NVIDIA GPU
            result = subprocess.run(['nvidia-smi'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return True
                
            # Check for AMD GPU (future implementation)
            # Check for Intel GPU (future implementation)
            
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
            
    async def enhance_video(self, file_path: str, parameters: Dict[str, Any]) -> str:
        """
        Enhance video quality using the best available method
        
        Args:
            file_path: Path to input video file
            parameters: Enhancement parameters
            
        Returns:
            Path to enhanced video file
        """
        try:
            enhancement_type = parameters.get('type', 'general')
            output_path = self._generate_output_path(file_path, f"enhanced_{enhancement_type}")
            
            if enhancement_type == 'upscale_2k':
                return await self.upscale_video(file_path, {'resolution': '2k'})
            elif enhancement_type == 'upscale_4k':
                return await self.upscale_video(file_path, {'resolution': '4k'})
            elif enhancement_type == 'denoise':
                return await self.denoise_audio(file_path, parameters)
            elif enhancement_type == 'enhance':
                # Apply general enhancement filters
                return await self.apply_enhancement_filters(file_path, parameters)
            else:
                # Default enhancement
                return await self.apply_enhancement_filters(file_path, parameters)
                
        except Exception as e:
            logger.error(f"Error enhancing video: {e}")
            raise
            
    async def upscale_video(self, file_path: str, parameters: Dict[str, Any]) -> str:
        """
        Upscale video resolution using Real-ESRGAN or fallback methods
        
        Args:
            file_path: Path to input video
            parameters: Upscaling parameters (resolution, model, etc.)
            
        Returns:
            Path to upscaled video
        """
        try:
            resolution = parameters.get('resolution', '2k')
            model = parameters.get('model', 'RealESRGAN_x4plus')
            
            if self.available_tools['realesrgan']:
                logger.info(f"Using Real-ESRGAN for upscaling to {resolution}")
                return await self.realesrgan.upscale(file_path, resolution, model)
            elif self.available_tools['video2x']:
                logger.info(f"Using Video2X for upscaling to {resolution}")
                return await self.video2x.upscale(file_path, resolution)
            elif self.available_tools['ffmpeg']:
                logger.info(f"Using FFmpeg for basic upscaling to {resolution}")
                return await self.ffmpeg.upscale(file_path, resolution)
            else:
                raise RuntimeError("No upscaling tools available")
                
        except Exception as e:
            logger.error(f"Error upscaling video: {e}")
            raise
            
    async def denoise_audio(self, file_path: str, parameters: Dict[str, Any]) -> str:
        """
        Remove noise from audio or video files
        
        Args:
            file_path: Path to input file
            parameters: Denoising parameters
            
        Returns:
            Path to denoised file
        """
        try:
            if not self.available_tools['ffmpeg']:
                raise RuntimeError("FFmpeg not available for denoising")
                
            level = parameters.get('level', 'medium')
            return await self.ffmpeg.denoise(file_path, level)
            
        except Exception as e:
            logger.error(f"Error denoising audio: {e}")
            raise
            
    async def convert_format(self, file_path: str, parameters: Dict[str, Any]) -> str:
        """
        Convert media file to different format
        
        Args:
            file_path: Path to input file
            parameters: Conversion parameters (format, quality, etc.)
            
        Returns:
            Path to converted file
        """
        try:
            if not self.available_tools['ffmpeg']:
                raise RuntimeError("FFmpeg not available for format conversion")
                
            output_format = parameters.get('format', 'mp4')
            quality = parameters.get('quality', 'high')
            
            return await self.ffmpeg.convert(file_path, output_format, quality)
            
        except Exception as e:
            logger.error(f"Error converting format: {e}")
            raise
            
    async def analyze_media(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze media file properties and metadata
        
        Args:
            file_path: Path to media file
            
        Returns:
            Dictionary with file analysis results
        """
        try:
            if not self.available_tools['ffmpeg']:
                raise RuntimeError("FFmpeg not available for media analysis")
                
            return await self.ffmpeg.analyze(file_path)
            
        except Exception as e:
            logger.error(f"Error analyzing media: {e}")
            raise
            
    async def apply_enhancement_filters(self, file_path: str, parameters: Dict[str, Any]) -> str:
        """
        Apply general enhancement filters to improve video quality
        
        Args:
            file_path: Path to input video
            parameters: Enhancement parameters
            
        Returns:
            Path to enhanced video
        """
        try:
            if not self.available_tools['ffmpeg']:
                raise RuntimeError("FFmpeg not available for enhancement")
                
            # Apply a combination of filters for general enhancement
            filters = []
            
            # Denoising
            if parameters.get('denoise', True):
                filters.append('hqdn3d=2:1:2:3')
                
            # Sharpening
            if parameters.get('sharpen', True):
                filters.append('unsharp=5:5:1.0:5:5:0.0')
                
            # Color enhancement
            if parameters.get('enhance_colors', True):
                filters.append('eq=contrast=1.1:brightness=0.1:saturation=1.2')
                
            # Stabilization (if requested)
            if parameters.get('stabilize', False):
                filters.append('vidstabdetect=stepsize=6:shakiness=8:accuracy=9')
                
            filter_string = ','.join(filters) if filters else 'copy'
            
            return await self.ffmpeg.apply_filters(file_path, filter_string)
            
        except Exception as e:
            logger.error(f"Error applying enhancement filters: {e}")
            raise
            
    async def batch_process(self, file_paths: list, operation: str, parameters: Dict[str, Any]) -> list:
        """
        Process multiple files with the same operation
        
        Args:
            file_paths: List of input file paths
            operation: Operation to perform
            parameters: Operation parameters
            
        Returns:
            List of output file paths
        """
        try:
            tasks = []
            
            for file_path in file_paths:
                if operation == 'enhance':
                    task = self.enhance_video(file_path, parameters)
                elif operation == 'upscale':
                    task = self.upscale_video(file_path, parameters)
                elif operation == 'denoise':
                    task = self.denoise_audio(file_path, parameters)
                elif operation == 'convert':
                    task = self.convert_format(file_path, parameters)
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                    
                tasks.append(task)
                
            # Process files concurrently (with reasonable limit)
            semaphore = asyncio.Semaphore(3)  # Limit concurrent processing
            
            async def process_with_semaphore(task):
                async with semaphore:
                    return await task
                    
            results = await asyncio.gather(
                *[process_with_semaphore(task) for task in tasks],
                return_exceptions=True
            )
            
            # Filter out exceptions and log errors
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing {file_paths[i]}: {result}")
                else:
                    successful_results.append(result)
                    
            return successful_results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            raise
            
    def _generate_output_path(self, input_path: str, suffix: str) -> str:
        """Generate output file path with suffix"""
        input_path = Path(input_path)
        output_dir = Path("media")
        output_dir.mkdir(exist_ok=True)
        
        output_name = f"{input_path.stem}_{suffix}{input_path.suffix}"
        return str(output_dir / output_name)
        
    def get_tool_status(self) -> Dict[str, bool]:
        """Get current status of all tools"""
        return self.available_tools.copy()
    
    def get_tools_status(self) -> Dict[str, bool]:
        """Get current status of all tools (alias for compatibility)"""
        return self.available_tools.copy()
        
    async def estimate_processing_time(self, file_path: str, operation: str, parameters: Dict) -> int:
        """
        Estimate processing time in seconds
        
        Args:
            file_path: Path to input file
            operation: Operation to perform
            parameters: Operation parameters
            
        Returns:
            Estimated time in seconds
        """
        try:
            # Get file info for estimation
            file_info = await self.analyze_media(file_path)
            file_size = Path(file_path).stat().st_size
            duration = file_info.get('duration', 60)  # Default 1 minute
            
            # Base estimation factors
            base_time = duration * 0.5  # Base processing time
            
            # Adjust based on operation
            if operation == 'upscale':
                resolution = parameters.get('resolution', '2k')
                if resolution == '4k':
                    base_time *= 4
                elif resolution == '2k':
                    base_time *= 2
                    
            elif operation == 'enhance':
                base_time *= 1.5
                
            elif operation == 'convert':
                base_time *= 0.3
                
            # Adjust based on available hardware
            if self.available_tools['gpu']:
                base_time *= 0.3  # GPU acceleration
                
            # File size factor
            size_factor = min(file_size / (100 * 1024 * 1024), 3)  # Cap at 3x for large files
            base_time *= size_factor
            
            return max(int(base_time), 10)  # Minimum 10 seconds
            
        except Exception as e:
            logger.error(f"Error estimating processing time: {e}")
            return 60  # Default 1 minute
