"""
Real-ESRGAN Tool - AI-powered video upscaling
Handles Real-ESRGAN integration for high-quality video enhancement
"""

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class RealESRGANTool:
    """Real-ESRGAN wrapper for AI-powered video upscaling"""
    
    def __init__(self):
        self.realesrgan_path = self._find_realesrgan_executable()
        self.models_dir = Path("models/Real-ESRGAN")
        self.temp_dir = Path("temp/realesrgan")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    def _find_realesrgan_executable(self) -> Optional[str]:
        """Find Real-ESRGAN executable in system PATH or common locations"""
        # Common executable names
        exe_names = ['realesrgan-ncnn-vulkan', 'Real-ESRGAN', 'realesrgan']
        
        for exe_name in exe_names:
            if shutil.which(exe_name):
                return exe_name
                
        # Check common installation paths
        common_paths = [
            '/usr/local/bin/realesrgan-ncnn-vulkan',
            '/opt/Real-ESRGAN/realesrgan-ncnn-vulkan',
            './Real-ESRGAN/realesrgan-ncnn-vulkan',
            './realesrgan-ncnn-vulkan'
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
                
        return None
        
    async def is_available(self) -> bool:
        """Check if Real-ESRGAN is available"""
        if not self.realesrgan_path:
            return False
            
        try:
            # Test if the executable runs
            process = await asyncio.create_subprocess_exec(
                self.realesrgan_path, '-h',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except (FileNotFoundError, PermissionError):
            return False
            
    async def upscale(self, file_path: str, resolution: str, model: str = 'RealESRGAN_x4plus') -> str:
        """
        Upscale video using Real-ESRGAN
        
        Args:
            file_path: Path to input video
            resolution: Target resolution ('2k', '4k')
            model: Real-ESRGAN model to use
            
        Returns:
            Path to upscaled video
        """
        try:
            if not await self.is_available():
                raise RuntimeError("Real-ESRGAN not available")
                
            # Determine scale factor
            scale_factor = self._get_scale_factor(resolution)
            
            # For video files, we need to extract frames, upscale, and reassemble
            return await self._upscale_video_frames(file_path, scale_factor, model)
            
        except Exception as e:
            logger.error(f"Error upscaling with Real-ESRGAN: {e}")
            raise
            
    async def _upscale_video_frames(self, video_path: str, scale_factor: int, model: str) -> str:
        """
        Upscale video by processing individual frames
        
        Args:
            video_path: Path to input video
            scale_factor: Upscaling factor (2, 4, etc.)
            model: Real-ESRGAN model name
            
        Returns:
            Path to upscaled video
        """
        try:
            video_path = Path(video_path)
            temp_video_dir = self.temp_dir / f"video_{video_path.stem}"
            temp_video_dir.mkdir(exist_ok=True)
            
            frames_dir = temp_video_dir / "frames"
            upscaled_dir = temp_video_dir / "upscaled"
            frames_dir.mkdir(exist_ok=True)
            upscaled_dir.mkdir(exist_ok=True)
            
            # Step 1: Extract frames from video
            await self._extract_frames(str(video_path), str(frames_dir))
            
            # Step 2: Upscale frames using Real-ESRGAN
            await self._upscale_frames(str(frames_dir), str(upscaled_dir), scale_factor, model)
            
            # Step 3: Reassemble video from upscaled frames
            output_path = self._generate_output_path(str(video_path), f"realesrgan_{scale_factor}x")
            await self._reassemble_video(str(upscaled_dir), str(video_path), output_path)
            
            # Cleanup temporary files
            shutil.rmtree(temp_video_dir)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in frame-based upscaling: {e}")
            # Cleanup on error
            if temp_video_dir.exists():
                shutil.rmtree(temp_video_dir)
            raise
            
    async def _extract_frames(self, video_path: str, frames_dir: str):
        """Extract frames from video using FFmpeg"""
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', 'fps=24',  # Limit to 24 fps for processing speed
            '-q:v', '1',  # High quality frames
            f'{frames_dir}/frame_%06d.png',
            '-y'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Frame extraction failed: {stderr.decode()}")
            
    async def _upscale_frames(self, frames_dir: str, output_dir: str, scale_factor: int, model: str):
        """Upscale frames using Real-ESRGAN"""
        if not self.realesrgan_path:
            raise RuntimeError("Real-ESRGAN executable not found")
            
        # Get available models
        model_file = self._get_model_file(model, scale_factor)
        
        cmd = [
            self.realesrgan_path,
            '-i', frames_dir,
            '-o', output_dir,
            '-n', model_file,
            '-s', str(scale_factor),
            '-f', 'png'
        ]
        
        # Add GPU acceleration if available
        if await self._has_vulkan_support():
            cmd.extend(['-g', '0'])  # Use first GPU
            
        logger.info(f"Running Real-ESRGAN: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Real-ESRGAN upscaling failed: {stderr.decode()}")
            
    async def _reassemble_video(self, frames_dir: str, original_video: str, output_path: str):
        """Reassemble video from upscaled frames"""
        # Get original video frame rate
        get_fps_cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'csv=p=0',
            original_video
        ]
        
        process = await asyncio.create_subprocess_exec(
            *get_fps_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        fps = "24"  # Default fallback
        
        if process.returncode == 0:
            fps_output = stdout.decode().strip()
            if '/' in fps_output:
                num, den = fps_output.split('/')
                fps = str(int(float(num) / float(den)))
                
        # Reassemble video
        cmd = [
            'ffmpeg',
            '-framerate', fps,
            '-i', f'{frames_dir}/frame_%06d.png',
            '-i', original_video,  # For audio track
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'slow',
            '-c:a', 'copy',  # Copy audio from original
            '-map', '0:v:0',  # Video from frames
            '-map', '1:a:0?',  # Audio from original (if exists)
            '-y',
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Video reassembly failed: {stderr.decode()}")
            
    def _get_scale_factor(self, resolution: str) -> int:
        """Get appropriate scale factor for target resolution"""
        resolution_map = {
            '2k': 2,
            '4k': 4,
            '1080p': 2,
            '720p': 1
        }
        return resolution_map.get(resolution.lower(), 2)
        
    def _get_model_file(self, model: str, scale_factor: int) -> str:
        """Get appropriate model file for the scale factor"""
        # Default models based on scale factor
        if scale_factor == 4:
            return 'RealESRGAN_x4plus'
        elif scale_factor == 2:
            return 'RealESRGAN_x2plus'
        else:
            return 'RealESRGAN_x4plus'
            
    async def _has_vulkan_support(self) -> bool:
        """Check if system has Vulkan support for GPU acceleration"""
        try:
            # Check for vulkan-utils
            process = await asyncio.create_subprocess_exec(
                'vulkaninfo',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except FileNotFoundError:
            return False
            
    def _generate_output_path(self, input_path: str, suffix: str) -> str:
        """Generate output file path"""
        input_path = Path(input_path)
        output_dir = Path("media")
        output_dir.mkdir(exist_ok=True)
        
        output_name = f"{input_path.stem}_{suffix}{input_path.suffix}"
        return str(output_dir / output_name)
        
    async def upscale_image(self, image_path: str, scale_factor: int = 4, model: str = 'RealESRGAN_x4plus') -> str:
        """
        Upscale a single image using Real-ESRGAN
        
        Args:
            image_path: Path to input image
            scale_factor: Upscaling factor
            model: Real-ESRGAN model to use
            
        Returns:
            Path to upscaled image
        """
        try:
            if not await self.is_available():
                raise RuntimeError("Real-ESRGAN not available")
                
            output_path = self._generate_output_path(image_path, f"upscaled_{scale_factor}x")
            
            cmd = [
                self.realesrgan_path,
                '-i', image_path,
                '-o', output_path,
                '-n', model,
                '-s', str(scale_factor)
            ]
            
            if await self._has_vulkan_support():
                cmd.extend(['-g', '0'])
                
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Image upscaling failed: {stderr.decode()}")
                
            return output_path
            
        except Exception as e:
            logger.error(f"Error upscaling image: {e}")
            raise
