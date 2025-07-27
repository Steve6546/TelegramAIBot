"""
FFmpeg Tool - Wrapper for FFmpeg operations
Handles video/audio processing, format conversion, and analysis
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FFmpegTool:
    """FFmpeg wrapper for media processing operations"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        
    async def is_available(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            result = await asyncio.create_subprocess_exec(
                self.ffmpeg_path, '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except FileNotFoundError:
            return False
            
    async def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze media file and extract metadata
        
        Args:
            file_path: Path to media file
            
        Returns:
            Dictionary with file analysis results
        """
        try:
            # Use ffprobe to get detailed file information
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {stderr.decode()}")
                
            probe_data = json.loads(stdout.decode())
            
            # Extract relevant information
            format_info = probe_data.get('format', {})
            streams = probe_data.get('streams', [])
            
            # Find video and audio streams
            video_stream = next((s for s in streams if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in streams if s['codec_type'] == 'audio'), None)
            
            analysis = {
                'format': format_info.get('format_name', 'unknown'),
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'streams': len(streams)
            }
            
            if video_stream:
                analysis['video'] = {
                    'codec': video_stream.get('codec_name', 'unknown'),
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                    'bitrate': int(video_stream.get('bit_rate', 0)),
                    'pixel_format': video_stream.get('pix_fmt', 'unknown')
                }
                analysis['resolution'] = f"{analysis['video']['width']}x{analysis['video']['height']}"
                
            if audio_stream:
                analysis['audio'] = {
                    'codec': audio_stream.get('codec_name', 'unknown'),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0)),
                    'bitrate': int(audio_stream.get('bit_rate', 0))
                }
                
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            raise
            
    async def denoise(self, file_path: str, level: str = 'medium') -> str:
        """
        Remove noise from audio or video using FFmpeg filters
        
        Args:
            file_path: Path to input file
            level: Noise reduction level ('light', 'medium', 'strong')
            
        Returns:
            Path to denoised file
        """
        try:
            output_path = self._generate_output_path(file_path, f"denoised_{level}")
            
            # Choose filter parameters based on level
            if level == 'light':
                denoise_filter = 'hqdn3d=2:1:2:3'
                audio_filter = 'afftdn=nr=10:nf=-20'
            elif level == 'strong':
                denoise_filter = 'hqdn3d=4:3:6:4.5'
                audio_filter = 'afftdn=nr=25:nf=-25'
            else:  # medium
                denoise_filter = 'hqdn3d=3:2:4:3'
                audio_filter = 'afftdn=nr=20:nf=-25'
                
            # Determine if file has video or just audio
            analysis = await self.analyze(file_path)
            has_video = 'video' in analysis
            
            if has_video:
                # Process both video and audio
                cmd = [
                    self.ffmpeg_path,
                    '-i', file_path,
                    '-vf', denoise_filter,
                    '-af', audio_filter,
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-y',  # Overwrite output file
                    output_path
                ]
            else:
                # Audio only
                cmd = [
                    self.ffmpeg_path,
                    '-i', file_path,
                    '-af', audio_filter,
                    '-c:a', 'aac',
                    '-y',
                    output_path
                ]
                
            await self._run_ffmpeg_command(cmd)
            return output_path
            
        except Exception as e:
            logger.error(f"Error denoising file: {e}")
            raise
            
    async def convert(self, file_path: str, output_format: str, quality: str = 'high') -> str:
        """
        Convert media file to different format
        
        Args:
            file_path: Path to input file
            output_format: Target format (mp4, avi, mov, mp3, wav, etc.)
            quality: Quality level ('low', 'medium', 'high')
            
        Returns:
            Path to converted file
        """
        try:
            # Generate output path with new extension
            input_path = Path(file_path)
            output_path = self._generate_output_path(file_path, f"converted.{output_format}")
            
            # Choose codec and quality settings
            video_codec, audio_codec, quality_params = self._get_conversion_params(
                output_format, quality
            )
            
            cmd = [
                self.ffmpeg_path,
                '-i', file_path,
                '-c:v', video_codec,
                '-c:a', audio_codec,
                *quality_params,
                '-y',
                output_path
            ]
            
            # Remove video codec for audio-only formats
            if output_format.lower() in ['mp3', 'wav', 'aac', 'flac', 'ogg']:
                cmd = [c for c in cmd if c not in ['-c:v', video_codec]]
                
            await self._run_ffmpeg_command(cmd)
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting file: {e}")
            raise
            
    async def upscale(self, file_path: str, resolution: str) -> str:
        """
        Basic upscaling using FFmpeg (fallback when Real-ESRGAN unavailable)
        
        Args:
            file_path: Path to input video
            resolution: Target resolution ('720p', '1080p', '2k', '4k')
            
        Returns:
            Path to upscaled video
        """
        try:
            output_path = self._generate_output_path(file_path, f"upscaled_{resolution}")
            
            # Get target dimensions
            width, height = self._get_resolution_dimensions(resolution)
            
            # Use lanczos scaling filter for better quality
            scale_filter = f'scale={width}:{height}:flags=lanczos'
            
            cmd = [
                self.ffmpeg_path,
                '-i', file_path,
                '-vf', scale_filter,
                '-c:v', 'libx264',
                '-crf', '18',  # High quality
                '-preset', 'slow',
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-y',
                output_path
            ]
            
            await self._run_ffmpeg_command(cmd)
            return output_path
            
        except Exception as e:
            logger.error(f"Error upscaling video: {e}")
            raise
            
    async def apply_filters(self, file_path: str, filter_string: str) -> str:
        """
        Apply custom filter chain to video
        
        Args:
            file_path: Path to input video
            filter_string: FFmpeg filter string
            
        Returns:
            Path to filtered video
        """
        try:
            output_path = self._generate_output_path(file_path, "filtered")
            
            cmd = [
                self.ffmpeg_path,
                '-i', file_path,
                '-vf', filter_string,
                '-c:v', 'libx264',
                '-c:a', 'copy',
                '-y',
                output_path
            ]
            
            await self._run_ffmpeg_command(cmd)
            return output_path
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            raise
            
    def _get_conversion_params(self, output_format: str, quality: str) -> tuple:
        """Get codec and quality parameters for conversion"""
        format_lower = output_format.lower()
        
        # Video codec selection
        if format_lower in ['mp4', 'mov']:
            video_codec = 'libx264'
        elif format_lower in ['avi']:
            video_codec = 'libx264'
        elif format_lower in ['mkv']:
            video_codec = 'libx264'
        else:
            video_codec = 'copy'
            
        # Audio codec selection
        if format_lower in ['mp4', 'mov', 'mkv']:
            audio_codec = 'aac'
        elif format_lower in ['avi']:
            audio_codec = 'mp3'
        elif format_lower == 'mp3':
            audio_codec = 'mp3'
        elif format_lower == 'wav':
            audio_codec = 'pcm_s16le'
        elif format_lower == 'aac':
            audio_codec = 'aac'
        else:
            audio_codec = 'copy'
            
        # Quality parameters
        if quality == 'low':
            quality_params = ['-crf', '28', '-preset', 'fast']
        elif quality == 'high':
            quality_params = ['-crf', '18', '-preset', 'slow']
        else:  # medium
            quality_params = ['-crf', '23', '-preset', 'medium']
            
        return video_codec, audio_codec, quality_params
        
    def _get_resolution_dimensions(self, resolution: str) -> tuple:
        """Get width and height for resolution string"""
        resolution_map = {
            '720p': (1280, 720),
            '1080p': (1920, 1080),
            '2k': (2560, 1440),
            '4k': (3840, 2160)
        }
        return resolution_map.get(resolution.lower(), (1920, 1080))
        
    async def _run_ffmpeg_command(self, cmd: list):
        """Run FFmpeg command and handle errors"""
        try:
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"FFmpeg command failed: {error_msg}")
                
            logger.info("FFmpeg command completed successfully")
            
        except Exception as e:
            logger.error(f"Error running FFmpeg command: {e}")
            raise
            
    def _generate_output_path(self, input_path: str, suffix: str) -> str:
        """Generate output file path with suffix"""
        input_path = Path(input_path)
        output_dir = Path("media")
        output_dir.mkdir(exist_ok=True)
        
        if '.' in suffix:  # suffix includes extension
            output_name = f"{input_path.stem}_{suffix}"
        else:
            output_name = f"{input_path.stem}_{suffix}{input_path.suffix}"
            
        return str(output_dir / output_name)
