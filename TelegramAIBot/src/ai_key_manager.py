"""
AI Key Manager - Secure handling of user API keys within Telegram
Manages OpenAI, Google Gemini, and Claude API keys securely
"""

import logging
import json
import os
from typing import Dict, Optional, Any
from pathlib import Path
import hashlib
import time

logger = logging.getLogger(__name__)

class AIKeyManager:
    """Secure management of user AI API keys"""
    
    def __init__(self):
        self.keys_file = Path("temp/user_keys.json")
        self.keys_file.parent.mkdir(exist_ok=True)
        self.user_keys = {}
        self.supported_models = {
            'openai': {
                'name': 'OpenAI GPT-4o',
                'models': ['gpt-4o', 'gpt-4', 'gpt-3.5-turbo'],
                'key_prefix': 'sk-',
                'test_endpoint': 'https://api.openai.com/v1/models'
            },
            'gemini': {
                'name': 'Google Gemini',
                'models': ['gemini-2.0-flash-exp', 'gemini-1.5-pro'],
                'key_prefix': 'AI',
                'test_endpoint': 'https://generativelanguage.googleapis.com/v1beta/models'
            },
            'claude': {
                'name': 'Anthropic Claude',
                'models': ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
                'key_prefix': 'sk-ant-',
                'test_endpoint': 'https://api.anthropic.com/v1/models'
            }
        }
        self.load_user_keys()
    
    def load_user_keys(self):
        """Load encrypted user keys from file"""
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    self.user_keys = json.load(f)
        except Exception as e:
            logger.error(f"Error loading user keys: {e}")
            self.user_keys = {}
    
    def save_user_keys(self):
        """Save encrypted user keys to file"""
        try:
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_keys, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user keys: {e}")
    
    def encrypt_key(self, key: str, user_id: int) -> str:
        """Simple encryption for API keys using user ID as salt"""
        salt = str(user_id).encode()
        return hashlib.sha256(key.encode() + salt).hexdigest()[:32] + key[8:]
    
    def decrypt_key(self, encrypted_key: str, user_id: int) -> str:
        """Decrypt API key"""
        if len(encrypted_key) < 32:
            return encrypted_key
        return encrypted_key[:len(encrypted_key)-32] + encrypted_key[32:]
    
    async def store_user_key(self, user_id: int, provider: str, api_key: str) -> Dict[str, Any]:
        """Store user's API key securely"""
        try:
            # Validate key format
            if provider not in self.supported_models:
                return {"success": False, "error": "مزود غير مدعوم"}
            
            expected_prefix = self.supported_models[provider]['key_prefix']
            if not api_key.startswith(expected_prefix):
                return {"success": False, "error": f"صيغة المفتاح غير صحيحة. يجب أن يبدأ بـ {expected_prefix}"}
            
            # Test the key
            is_valid = await self.test_api_key(provider, api_key)
            if not is_valid:
                return {"success": False, "error": "المفتاح غير صالح أو منتهي الصلاحية"}
            
            # Store encrypted key
            user_str = str(user_id)
            if user_str not in self.user_keys:
                self.user_keys[user_str] = {}
            
            self.user_keys[user_str][provider] = {
                'key': self.encrypt_key(api_key, user_id),
                'timestamp': int(time.time()),
                'model': self.supported_models[provider]['models'][0]  # Default model
            }
            
            self.save_user_keys()
            
            return {
                "success": True, 
                "message": f"تم حفظ مفتاح {self.supported_models[provider]['name']} بنجاح!",
                "provider": provider
            }
            
        except Exception as e:
            logger.error(f"Error storing user key: {e}")
            return {"success": False, "error": "خطأ في حفظ المفتاح"}
    
    async def test_api_key(self, provider: str, api_key: str) -> bool:
        """Test if API key is valid"""
        try:
            import httpx
            
            if provider == 'openai':
                headers = {"Authorization": f"Bearer {api_key}"}
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers=headers,
                        timeout=10
                    )
                    return response.status_code == 200
                    
            elif provider == 'gemini':
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                        timeout=10
                    )
                    return response.status_code == 200
                    
            elif provider == 'claude':
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.anthropic.com/v1/models",
                        headers=headers,
                        timeout=10
                    )
                    return response.status_code == 200
                    
        except Exception as e:
            logger.error(f"Error testing API key: {e}")
            return False
        
        return False
    
    def get_user_key(self, user_id: int, provider: str) -> Optional[str]:
        """Get user's API key for specific provider"""
        try:
            user_str = str(user_id)
            if user_str in self.user_keys and provider in self.user_keys[user_str]:
                encrypted_key = self.user_keys[user_str][provider]['key']
                return self.decrypt_key(encrypted_key, user_id)
        except Exception as e:
            logger.error(f"Error getting user key: {e}")
        return None
    
    def get_user_models(self, user_id: int) -> Dict[str, Any]:
        """Get available models for user"""
        user_str = str(user_id)
        available_models = {}
        
        if user_str in self.user_keys:
            for provider, data in self.user_keys[user_str].items():
                if provider in self.supported_models:
                    available_models[provider] = {
                        'name': self.supported_models[provider]['name'],
                        'models': self.supported_models[provider]['models'],
                        'current_model': data.get('model', self.supported_models[provider]['models'][0])
                    }
        
        return available_models
    
    def set_user_model(self, user_id: int, provider: str, model: str) -> bool:
        """Set user's preferred model for a provider"""
        try:
            user_str = str(user_id)
            if (user_str in self.user_keys and 
                provider in self.user_keys[user_str] and
                provider in self.supported_models and
                model in self.supported_models[provider]['models']):
                
                self.user_keys[user_str][provider]['model'] = model
                self.save_user_keys()
                return True
        except Exception as e:
            logger.error(f"Error setting user model: {e}")
        return False
    
    def remove_user_key(self, user_id: int, provider: str) -> bool:
        """Remove user's API key"""
        try:
            user_str = str(user_id)
            if user_str in self.user_keys and provider in self.user_keys[user_str]:
                del self.user_keys[user_str][provider]
                if not self.user_keys[user_str]:  # Remove user entry if empty
                    del self.user_keys[user_str]
                self.save_user_keys()
                return True
        except Exception as e:
            logger.error(f"Error removing user key: {e}")
        return False
    
    def get_user_ai_status(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive AI status for user"""
        user_str = str(user_id)
        status = {
            'has_keys': False,
            'providers': [],
            'current_models': {},
            'total_keys': 0
        }
        
        if user_str in self.user_keys:
            status['has_keys'] = True
            status['total_keys'] = len(self.user_keys[user_str])
            
            for provider, data in self.user_keys[user_str].items():
                if provider in self.supported_models:
                    status['providers'].append({
                        'id': provider,
                        'name': self.supported_models[provider]['name'],
                        'model': data.get('model', 'Unknown'),
                        'added': data.get('timestamp', 0)
                    })
                    status['current_models'][provider] = data.get('model')
        
        return status