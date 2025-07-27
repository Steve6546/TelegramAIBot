"""
Utility Functions - Common helper functions
File validation, formatting, and general utilities
"""

import hashlib
import logging
import mimetypes
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import asyncio

logger = logging.getLogger(__name__)

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
        
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and size_index < len(size_names) - 1:
        size /= 1024
        size_index += 1
        
    return f"{size:.1f} {size_names[size_index]}"

def format_duration(seconds: int) -> str:
    """
    Format duration in human readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 0:
        return "غير معروف"
        
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def get_file_extension(file_path: str) -> str:
    """
    Get file extension from file path
    
    Args:
        file_path: Path to file
        
    Returns:
        File extension (including dot)
    """
    return Path(file_path).suffix.lower()

def get_file_type(file_path: str) -> str:
    """
    Determine file type from extension
    
    Args:
        file_path: Path to file
        
    Returns:
        File type ('video', 'audio', 'image', 'unknown')
    """
    extension = get_file_extension(file_path)
    
    video_extensions = {
        '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', 
        '.m4v', '.3gp', '.ts', '.mts', '.vob', '.ogv'
    }
    
    audio_extensions = {
        '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', 
        '.wma', '.opus', '.amr', '.ac3'
    }
    
    image_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', 
        '.webp', '.svg', '.ico'
    }
    
    if extension in video_extensions:
        return 'video'
    elif extension in audio_extensions:
        return 'audio'
    elif extension in image_extensions:
        return 'image'
    else:
        return 'unknown'

def is_valid_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL is valid
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def is_supported_video_url(url: str) -> bool:
    """
    Check if URL is from a supported video platform
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is from supported platform
    """
    if not is_valid_url(url):
        return False
        
    parsed = urlparse(url.lower())
    domain = parsed.netloc
    
    supported_domains = {
        'youtube.com', 'www.youtube.com', 'm.youtube.com',
        'youtu.be', 'youtube-nocookie.com',
        'vimeo.com', 'www.vimeo.com',
        'dailymotion.com', 'www.dailymotion.com',
        'twitch.tv', 'www.twitch.tv',
        'facebook.com', 'www.facebook.com', 'fb.watch',
        'instagram.com', 'www.instagram.com'
    }
    
    return any(domain.endswith(d) or domain == d for d in supported_domains)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem usage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(unsafe_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    if len(sanitized) > 200:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        max_name_length = 200 - len(ext)
        sanitized = name[:max_name_length] + ext
        
    # Ensure not empty
    if not sanitized or sanitized == '_':
        sanitized = 'file'
        
    return sanitized

def calculate_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """
    Calculate SHA-256 hash of file
    
    Args:
        file_path: Path to file
        chunk_size: Size of chunks to read
        
    Returns:
        Hexadecimal hash string
    """
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

def validate_file_size(file_path: str, max_size_mb: int = 50) -> bool:
    """
    Validate file size against maximum allowed
    
    Args:
        file_path: Path to file
        max_size_mb: Maximum size in megabytes
        
    Returns:
        True if file size is within limit
    """
    try:
        file_size = Path(file_path).stat().st_size
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
    except Exception:
        return False

def get_mime_type(file_path: str) -> str:
    """
    Get MIME type of file
    
    Args:
        file_path: Path to file
        
    Returns:
        MIME type string
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'

def is_video_file(file_path: str) -> bool:
    """Check if file is a video file"""
    return get_file_type(file_path) == 'video'

def is_audio_file(file_path: str) -> bool:
    """Check if file is an audio file"""
    return get_file_type(file_path) == 'audio'

def is_image_file(file_path: str) -> bool:
    """Check if file is an image file"""
    return get_file_type(file_path) == 'image'

def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract video ID from various video platform URLs
    
    Args:
        url: Video URL
        
    Returns:
        Video ID if found, None otherwise
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # YouTube
        if 'youtube.com' in domain:
            if 'watch' in parsed.path:
                # Standard YouTube URL
                query_params = dict(param.split('=') for param in parsed.query.split('&') if '=' in param)
                return query_params.get('v')
            elif 'embed' in parsed.path:
                # Embedded YouTube URL
                return parsed.path.split('/')[-1]
        elif 'youtu.be' in domain:
            # Short YouTube URL
            return parsed.path[1:]  # Remove leading slash
            
        # Vimeo
        elif 'vimeo.com' in domain:
            path_parts = parsed.path.strip('/').split('/')
            if path_parts:
                return path_parts[-1]  # Last part is usually the video ID
                
        # Dailymotion
        elif 'dailymotion.com' in domain:
            if '/video/' in parsed.path:
                return parsed.path.split('/video/')[-1].split('_')[0]
                
    except Exception as e:
        logger.error(f"Error extracting video ID from URL: {e}")
        
    return None

def create_progress_bar(current: int, total: int, width: int = 20) -> str:
    """
    Create ASCII progress bar
    
    Args:
        current: Current progress value
        total: Total value
        width: Width of progress bar
        
    Returns:
        ASCII progress bar string
    """
    if total == 0:
        return "█" * width
        
    progress = min(current / total, 1.0)
    filled = int(width * progress)
    bar = "█" * filled + "░" * (width - filled)
    percentage = int(progress * 100)
    
    return f"[{bar}] {percentage}%"

def parse_resolution_string(resolution: str) -> tuple:
    """
    Parse resolution string to width/height tuple
    
    Args:
        resolution: Resolution string (e.g., "1920x1080", "4K", "2K")
        
    Returns:
        Tuple of (width, height)
    """
    resolution = resolution.lower().strip()
    
    # Named resolutions
    named_resolutions = {
        '720p': (1280, 720),
        '1080p': (1920, 1080),
        '2k': (2560, 1440),
        '4k': (3840, 2160),
        '8k': (7680, 4320),
        'hd': (1280, 720),
        'fhd': (1920, 1080),
        'uhd': (3840, 2160)
    }
    
    if resolution in named_resolutions:
        return named_resolutions[resolution]
        
    # Try to parse "WIDTHxHEIGHT" format
    if 'x' in resolution:
        try:
            width, height = resolution.split('x')
            return (int(width), int(height))
        except ValueError:
            pass
            
    # Default to 1080p
    return (1920, 1080)

def format_processing_time(start_time: float, end_time: float) -> str:
    """
    Format processing time duration
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        Formatted time string
    """
    duration = end_time - start_time
    return format_duration(int(duration))

def validate_telegram_file_id(file_id: str) -> bool:
    """
    Validate Telegram file ID format
    
    Args:
        file_id: Telegram file ID
        
    Returns:
        True if valid format
    """
    # Basic validation - Telegram file IDs are typically base64-like strings
    if not file_id or len(file_id) < 10:
        return False
        
    # Check for valid characters
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
    return all(c in valid_chars for c in file_id)

async def run_command_async(command: List[str], timeout: int = 300) -> tuple:
    """
    Run command asynchronously with timeout
    
    Args:
        command: Command and arguments as list
        timeout: Timeout in seconds
        
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
        
        return process.returncode, stdout.decode(), stderr.decode()
        
    except asyncio.TimeoutError:
        if process:
            process.kill()
            await process.wait()
        raise TimeoutError(f"Command timed out after {timeout} seconds")
    except Exception as e:
        logger.error(f"Error running command {' '.join(command)}: {e}")
        raise

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix

def clean_filename_for_telegram(filename: str) -> str:
    """
    Clean filename for Telegram compatibility
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename safe for Telegram
    """
    # Remove problematic characters for Telegram
    cleaned = re.sub(r'[^\w\s\-_\.]', '', filename)
    
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove leading/trailing spaces
    cleaned = cleaned.strip()
    
    # Ensure reasonable length
    if len(cleaned) > 64:  # Telegram filename limit
        name, ext = Path(cleaned).stem, Path(cleaned).suffix
        max_name_length = 64 - len(ext)
        cleaned = name[:max_name_length] + ext
        
    return cleaned or "file"

def estimate_processing_complexity(file_info: Dict[str, Any]) -> str:
    """
    Estimate processing complexity based on file information
    
    Args:
        file_info: File information dictionary
        
    Returns:
        Complexity level ('low', 'medium', 'high')
    """
    try:
        file_size = file_info.get('size', 0)
        duration = file_info.get('duration', 0)
        resolution = file_info.get('resolution', '720x480')
        
        # Parse resolution
        width, height = parse_resolution_string(resolution)
        pixel_count = width * height
        
        # Calculate complexity score
        complexity_score = 0
        
        # File size factor (MB)
        size_mb = file_size / (1024 * 1024)
        if size_mb > 100:
            complexity_score += 3
        elif size_mb > 50:
            complexity_score += 2
        elif size_mb > 10:
            complexity_score += 1
            
        # Duration factor (minutes)
        duration_min = duration / 60
        if duration_min > 30:
            complexity_score += 3
        elif duration_min > 10:
            complexity_score += 2
        elif duration_min > 3:
            complexity_score += 1
            
        # Resolution factor
        if pixel_count > 8000000:  # 4K+
            complexity_score += 3
        elif pixel_count > 2000000:  # 1080p+
            complexity_score += 2
        elif pixel_count > 900000:  # 720p+
            complexity_score += 1
            
        # Determine complexity level
        if complexity_score >= 6:
            return 'high'
        elif complexity_score >= 3:
            return 'medium'
        else:
            return 'low'
            
    except Exception as e:
        logger.error(f"Error estimating processing complexity: {e}")
        return 'medium'  # Default to medium
