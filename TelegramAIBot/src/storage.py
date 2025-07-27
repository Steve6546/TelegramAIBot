"""
Storage Manager - Handles file operations and cleanup
Manages downloads, temporary files, and processed outputs
"""

import asyncio
import hashlib
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import json

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages file storage and cleanup operations"""
    
    def __init__(self):
        self.base_dir = Path(".")
        self.downloads_dir = self.base_dir / "downloads"
        self.temp_dir = self.base_dir / "temp"
        self.media_dir = self.base_dir / "media"
        self.logs_dir = self.base_dir / "logs"
        
        # Create directories
        for directory in [self.downloads_dir, self.temp_dir, self.media_dir, self.logs_dir]:
            directory.mkdir(exist_ok=True)
            
        self.user_context_file = self.base_dir / "user_context.json"
        self.file_registry = self.base_dir / "file_registry.json"
        
        # Load existing data
        self.user_contexts = self._load_user_contexts()
        self.file_index = self._load_file_registry()
        
    def _load_user_contexts(self) -> Dict:
        """Load user contexts from file"""
        try:
            if self.user_context_file.exists():
                with open(self.user_context_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user contexts: {e}")
        return {}
        
    def _save_user_contexts(self):
        """Save user contexts to file"""
        try:
            with open(self.user_context_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_contexts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving user contexts: {e}")
            
    def _load_file_registry(self) -> Dict:
        """Load file registry from file"""
        try:
            if self.file_registry.exists():
                with open(self.file_registry, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading file registry: {e}")
        return {}
        
    def _save_file_registry(self):
        """Save file registry to file"""
        try:
            with open(self.file_registry, 'w', encoding='utf-8') as f:
                json.dump(self.file_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving file registry: {e}")
            
    async def download_file(self, url: str, user_id: int) -> str:
        """
        Download file from URL
        
        Args:
            url: URL to download from
            user_id: User ID for organizing files
            
        Returns:
            Path to downloaded file
        """
        try:
            import yt_dlp
            
            # Create user-specific download directory
            user_dir = self.downloads_dir / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Configure yt-dlp options
            ydl_opts = {
                'outtmpl': str(user_dir / '%(title)s.%(ext)s'),
                'format': 'best[filesize<50M]/best',  # Limit file size
                'noplaylist': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get info first
                info = ydl.extract_info(url, download=False)
                
                # Check file size
                filesize = info.get('filesize') or info.get('filesize_approx', 0)
                if filesize > 50 * 1024 * 1024:  # 50MB limit
                    raise ValueError("File too large (max 50MB)")
                    
                # Download the file
                ydl.download([url])
                
                # Find the downloaded file
                title = info.get('title', 'download')
                ext = info.get('ext', 'mp4')
                file_path = user_dir / f"{title}.{ext}"
                
                if not file_path.exists():
                    # Try to find the actual downloaded file
                    downloaded_files = list(user_dir.glob('*'))
                    if downloaded_files:
                        file_path = downloaded_files[-1]  # Get the most recent
                    else:
                        raise FileNotFoundError("Downloaded file not found")
                        
                # Register the file
                file_info = {
                    'user_id': user_id,
                    'original_url': url,
                    'download_time': datetime.now().isoformat(),
                    'file_size': file_path.stat().st_size,
                    'file_type': self._get_file_type(str(file_path))
                }
                
                self.register_file(str(file_path), file_info)
                await self.update_user_context(user_id, 'recent_download', str(file_path))
                
                logger.info(f"Successfully downloaded {url} to {file_path}")
                return str(file_path)
                
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {e}")
            raise
            
    async def save_telegram_file(self, file, user_id: int) -> str:
        """
        Save file from Telegram
        
        Args:
            file: Telegram file object
            user_id: User ID
            
        Returns:
            Path to saved file
        """
        try:
            # Create user-specific directory
            user_dir = self.downloads_dir / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = self._get_extension_from_mime(getattr(file, 'mime_type', ''))
            filename = f"telegram_{timestamp}{file_extension}"
            file_path = user_dir / filename
            
            # Download the file
            downloaded_file = await file.download_to_drive(str(file_path))
            
            # Register the file
            file_info = {
                'user_id': user_id,
                'source': 'telegram',
                'file_id': file.file_id,
                'upload_time': datetime.now().isoformat(),
                'file_size': file.file_size,
                'mime_type': getattr(file, 'mime_type', ''),
                'file_type': self._get_file_type(str(file_path))
            }
            
            self.register_file(str(file_path), file_info)
            await self.update_user_context(user_id, 'recent_upload', str(file_path))
            
            logger.info(f"Saved Telegram file to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving Telegram file: {e}")
            raise
            
    def register_file(self, file_path: str, info: Dict):
        """Register file in the file index"""
        file_hash = self._calculate_file_hash(file_path)
        self.file_index[file_hash] = {
            'path': file_path,
            'info': info,
            'registered_at': datetime.now().isoformat()
        }
        self._save_file_registry()
        
    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """Get file information from registry"""
        file_hash = self._calculate_file_hash(file_path)
        return self.file_index.get(file_hash)
        
    async def get_user_context(self, user_id: int) -> Dict:
        """Get user context information"""
        return self.user_contexts.get(str(user_id), {
            'recent_files': [],
            'preferred_settings': {},
            'total_processed': 0,
            'last_activity': None
        })
        
    async def update_user_context(self, user_id: int, key: str, value):
        """Update user context"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_contexts:
            self.user_contexts[user_id_str] = {
                'recent_files': [],
                'preferred_settings': {},
                'total_processed': 0,
                'last_activity': None
            }
            
        if key == 'recent_upload' or key == 'recent_download':
            # Add to recent files list (keep last 5)
            recent_files = self.user_contexts[user_id_str]['recent_files']
            if value not in recent_files:
                recent_files.insert(0, value)
                self.user_contexts[user_id_str]['recent_files'] = recent_files[:5]
        else:
            self.user_contexts[user_id_str][key] = value
            
        self.user_contexts[user_id_str]['last_activity'] = datetime.now().isoformat()
        self._save_user_contexts()
        
    def create_temp_file(self, suffix: str = '', user_id: Optional[int] = None) -> str:
        """
        Create temporary file path
        
        Args:
            suffix: File suffix/extension
            user_id: Optional user ID for organization
            
        Returns:
            Path to temporary file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        if user_id:
            temp_dir = self.temp_dir / str(user_id)
            temp_dir.mkdir(exist_ok=True)
        else:
            temp_dir = self.temp_dir
            
        filename = f"temp_{timestamp}{suffix}"
        return str(temp_dir / filename)
        
    def move_to_media(self, temp_path: str, final_name: str) -> str:
        """
        Move file from temp to media directory
        
        Args:
            temp_path: Current temporary file path
            final_name: Final filename
            
        Returns:
            Path to file in media directory
        """
        try:
            temp_path = Path(temp_path)
            media_path = self.media_dir / final_name
            
            # Ensure unique filename
            counter = 1
            original_media_path = media_path
            while media_path.exists():
                stem = original_media_path.stem
                suffix = original_media_path.suffix
                media_path = self.media_dir / f"{stem}_{counter}{suffix}"
                counter += 1
                
            # Move the file
            shutil.move(str(temp_path), str(media_path))
            
            logger.info(f"Moved {temp_path} to {media_path}")
            return str(media_path)
            
        except Exception as e:
            logger.error(f"Error moving file to media directory: {e}")
            raise
            
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up temporary files older than specified hours
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            for temp_file in self.temp_dir.rglob("*"):
                if temp_file.is_file():
                    file_time = datetime.fromtimestamp(temp_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        temp_file.unlink()
                        cleaned_count += 1
                        
            logger.info(f"Cleaned up {cleaned_count} temporary files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
            return 0
            
    def cleanup_user_files(self, user_id: int, max_age_hours: int = 168):  # 1 week
        """
        Clean up old files for a specific user
        
        Args:
            user_id: User ID
            max_age_hours: Maximum age in hours
        """
        try:
            user_dir = self.downloads_dir / str(user_id)
            if not user_dir.exists():
                return 0
                
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            for file_path in user_dir.rglob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
                        
            logger.info(f"Cleaned up {cleaned_count} files for user {user_id}")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up user files: {e}")
            return 0
            
    def get_disk_usage(self) -> Dict[str, int]:
        """Get disk usage statistics"""
        try:
            stats = {}
            
            for directory_name, directory_path in [
                ('downloads', self.downloads_dir),
                ('temp', self.temp_dir),
                ('media', self.media_dir),
                ('logs', self.logs_dir)
            ]:
                total_size = 0
                file_count = 0
                
                for file_path in directory_path.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1
                        
                stats[directory_name] = {
                    'size_bytes': total_size,
                    'size_mb': total_size / (1024 * 1024),
                    'file_count': file_count
                }
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {}
            
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return str(abs(hash(file_path)))
            
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type from extension"""
        extension = Path(file_path).suffix.lower()
        
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
        audio_extensions = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        
        if extension in video_extensions:
            return 'video'
        elif extension in audio_extensions:
            return 'audio'
        elif extension in image_extensions:
            return 'image'
        else:
            return 'unknown'
            
    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_map = {
            'video/mp4': '.mp4',
            'video/avi': '.avi',
            'video/quicktime': '.mov',
            'video/x-msvideo': '.avi',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/aac': '.aac',
            'audio/ogg': '.ogg',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif'
        }
        return mime_map.get(mime_type, '.bin')
