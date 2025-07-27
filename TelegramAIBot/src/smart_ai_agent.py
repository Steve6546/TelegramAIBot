"""
Smart AI Agent - Enhanced version with natural conversation handling
Handles Arabic and English commands with intelligent responses
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional
import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)

class SmartAIAgent:
    """Enhanced AI Agent for natural conversation and command processing"""
    
    def __init__(self, tool_manager):
        self.tool_manager = tool_manager
        
        # Initialize AI clients
        self.openai_client = None
        self.gemini_client = None
        
        # Check which AI services are available
        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
        if os.getenv("GOOGLE_API_KEY"):
            self.gemini_api_key = os.getenv("GOOGLE_API_KEY")
            self.gemini_client = httpx.AsyncClient()
            
        # Keywords for command recognition
        self.enhancement_keywords = {
            'arabic': ['حسن', 'تحسين', 'ارفع', 'زود', 'اعدل', 'حسين'],
            'english': ['enhance', 'improve', 'upscale', 'upgrade', 'better']
        }
        
        self.conversion_keywords = {
            'arabic': ['حول', 'غير', 'اجعل', 'عدل'],
            'english': ['convert', 'change', 'transform', 'make']
        }
        
        self.noise_keywords = {
            'arabic': ['نظف', 'ازالة', 'حذف', 'ضوضاء', 'تشويش'],
            'english': ['clean', 'remove', 'noise', 'denoise', 'clear']
        }
    
    async def process_natural_command(self, command: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process natural language command with enhanced conversation handling
        """
        try:
            logger.info(f"Smart AI processing: {command}")
            
            # Handle simple greetings and commands directly
            simple_response = self._handle_simple_commands(command)
            if simple_response:
                return simple_response
            
            # Analyze command for media processing intent
            analysis = self._analyze_command_intent(command, user_context)
            
            if analysis['has_clear_intent']:
                return analysis['response']
            
            # For complex commands, use AI if available
            if self.openai_client or self.gemini_client:
                ai_response = await self._process_with_ai(command, user_context)
                if ai_response:
                    return ai_response
            
            # Fallback to local processing
            return self._fallback_response(command)
            
        except Exception as e:
            logger.error(f"Error in smart AI processing: {e}")
            return {
                "action": "error",
                "message": "عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة مرة أخرى أو استخدام الأزرار التفاعلية.",
                "needs_file": False,
                "confidence": 0.0
            }
    
    def _handle_simple_commands(self, command: str) -> Optional[Dict[str, Any]]:
        """Handle simple commands without AI processing"""
        command_lower = command.lower().strip()
        
        # Greetings - Arabic and English
        greetings = ['هلا', 'اهلا', 'أهلا', 'السلام عليكم', 'مرحبا', 'مرحباً', 
                    'صباح الخير', 'مساء الخير', 'hi', 'hello', 'hey', 'سلام']
        
        if any(greeting in command_lower for greeting in greetings):
            return {
                "action": "greeting",
                "message": "🤖 أهلاً وسهلاً بك في Smart Media AI Assistant! 🎬\n\n"
                          "أنا مساعدك الذكي لتحسين جودة الفيديو والصوت.\n\n"
                          "📱 ما يمكنني فعله:\n"
                          "• تحسين جودة الفيديو ورفع الدقة\n"
                          "• إزالة الضوضاء من الصوت\n"
                          "• تحويل بين صيغ الملفات\n"
                          "• تحميل ومعالجة مقاطع من YouTube\n\n"
                          "🚀 ابدأ بإرسال ملف أو رابط، أو استخدم الأزرار الذكية!",
                "needs_file": False,
                "confidence": 1.0,
                "show_main_menu": True
            }
        
        # Help commands
        help_keywords = ['مساعدة', 'help', 'ساعدني', 'كيف', 'شلون', 'وش اسوي']
        if any(keyword in command_lower for keyword in help_keywords):
            return {
                "action": "help",
                "message": "📚 **دليل الاستخدام السريع**\n\n"
                          "🎬 **أوامر الفيديو:**\n"
                          "• 'حسن الفيديو' - تحسين عام\n"
                          "• 'ارفع الدقة' - رفع لـ 2K/4K\n"
                          "• 'نظف الصوت' - إزالة الضوضاء\n\n"
                          "🔄 **أوامر التحويل:**\n"
                          "• 'حول إلى MP4' - تحويل الفيديو\n"
                          "• 'حول إلى MP3' - استخراج الصوت\n\n"
                          "🤖 **أوامر ذكية:**\n"
                          "• 'معالجة ذكية' - تحليل وتحسين تلقائي\n"
                          "• 'اقترح تحسينات' - اقتراحات مخصصة\n\n"
                          "💡 استخدم الأزرار للوصول السريع!",
                "needs_file": False,
                "confidence": 1.0,
                "show_help_menu": True
            }
        
        # Status commands
        status_keywords = ['حالة', 'status', 'وضع', 'كيف النظام']
        if any(keyword in command_lower for keyword in status_keywords):
            return {
                "action": "status",
                "message": "📊 **حالة النظام**\n\n"
                          "✅ النظام يعمل بشكل طبيعي\n"
                          "✅ FFmpeg متاح للمعالجة\n"
                          "⚡ معالجة CPU نشطة\n"
                          "🔄 قائمة المهام جاهزة\n\n"
                          "🚀 النظام جاهز لمعالجة ملفاتك!",
                "needs_file": False,
                "confidence": 1.0,
                "show_status_menu": True
            }
        
        return None
    
    def _analyze_command_intent(self, command: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze command for clear media processing intent"""
        command_lower = command.lower()
        has_file = user_context and user_context.get('latest_file')
        
        # Enhancement intent
        if any(keyword in command_lower for keyword in self.enhancement_keywords['arabic'] + self.enhancement_keywords['english']):
            if '4k' in command_lower or '2160' in command_lower:
                action_type = 'upscale_4k'
                message = "🎯 فهمت! تريد رفع الدقة إلى 4K"
            elif '2k' in command_lower or '1440' in command_lower:
                action_type = 'upscale_2k'  
                message = "🎯 فهمت! تريد رفع الدقة إلى 2K"
            else:
                action_type = 'enhance'
                message = "🎯 فهمت! تريد تحسين جودة الملف"
            
            if has_file:
                return {
                    'has_clear_intent': True,
                    'response': {
                        "action": "enhance",
                        "parameters": {"type": action_type},
                        "message": f"{message}\n\n⚡ سأبدأ المعالجة الآن...",
                        "needs_file": False,
                        "confidence": 0.9
                    }
                }
            else:
                return {
                    'has_clear_intent': True,
                    'response': {
                        "action": "enhance",
                        "parameters": {"type": action_type},
                        "message": f"{message}\n\n📁 أرسل الملف أولاً للبدء في المعالجة",
                        "needs_file": True,
                        "confidence": 0.8
                    }
                }
        
        # Noise removal intent
        if any(keyword in command_lower for keyword in self.noise_keywords['arabic'] + self.noise_keywords['english']):
            if has_file:
                return {
                    'has_clear_intent': True,
                    'response': {
                        "action": "denoise",
                        "parameters": {"type": "audio_denoise"},
                        "message": "🎯 فهمت! تريد إزالة الضوضاء من الصوت\n\n⚡ سأبدأ التنظيف الآن...",
                        "needs_file": False,
                        "confidence": 0.9
                    }
                }
            else:
                return {
                    'has_clear_intent': True,
                    'response': {
                        "action": "denoise",
                        "parameters": {"type": "audio_denoise"},
                        "message": "🎯 فهمت! تريد إزالة الضوضاء من الصوت\n\n📁 أرسل الملف أولاً",
                        "needs_file": True,
                        "confidence": 0.8
                    }
                }
        
        # Conversion intent
        conversion_matches = re.findall(r'(?:حول|convert).*?(?:إلى|to)\s*(\w+)', command_lower)
        if conversion_matches or any(keyword in command_lower for keyword in self.conversion_keywords['arabic'] + self.conversion_keywords['english']):
            target_format = 'mp4'  # default
            if conversion_matches:
                target_format = conversion_matches[0].lower()
            elif 'mp3' in command_lower:
                target_format = 'mp3'
            elif 'mp4' in command_lower:
                target_format = 'mp4'
            elif 'avi' in command_lower:
                target_format = 'avi'
            
            if has_file:
                return {
                    'has_clear_intent': True,
                    'response': {
                        "action": "convert",
                        "parameters": {"format": target_format},
                        "message": f"🎯 فهمت! تريد التحويل إلى {target_format.upper()}\n\n⚡ سأبدأ التحويل الآن...",
                        "needs_file": False,
                        "confidence": 0.9
                    }
                }
            else:
                return {
                    'has_clear_intent': True,
                    'response': {
                        "action": "convert",
                        "parameters": {"format": target_format},
                        "message": f"🎯 فهمت! تريد التحويل إلى {target_format.upper()}\n\n📁 أرسل الملف أولاً",
                        "needs_file": True,
                        "confidence": 0.8
                    }
                }
        
        return {'has_clear_intent': False}
    
    async def _process_with_ai(self, command: str, user_context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Process complex commands using AI services"""
        try:
            system_prompt = """أنت مساعد ذكي متخصص في معالجة الوسائط. تتحدث العربية والإنجليزية.
مهمتك فهم أوامر المستخدم وتحديد الإجراء المناسب.

الإجراءات المتاحة:
- enhance: تحسين جودة الفيديو
- upscale: رفع دقة الفيديو (2K/4K)
- denoise: إزالة الضوضاء
- convert: تحويل الصيغ
- analyze: تحليل الملف

رد بشكل طبيعي ومفيد، ولا ترد بـ JSON. اشرح للمستخدم ما فهمته من طلبه."""

            user_prompt = f"المستخدم قال: {command}"
            
            if user_context and user_context.get('latest_file'):
                user_prompt += f"\nلدى المستخدم ملف: {user_context['latest_file']['name']}"
            
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                
                ai_message = response.choices[0].message.content
                
                # Parse AI response to determine action
                action = self._extract_action_from_ai_response(ai_message, command)
                
                return {
                    "action": action["type"],
                    "parameters": action["parameters"],
                    "message": ai_message,
                    "needs_file": action["needs_file"],
                    "confidence": 0.8
                }
                
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return None
    
    def _extract_action_from_ai_response(self, ai_message: str, original_command: str) -> Dict[str, Any]:
        """Extract action from AI response"""
        message_lower = (ai_message + " " + original_command).lower()
        
        if any(word in message_lower for word in ['تحسين', 'enhance', 'رفع', 'upscale']):
            if '4k' in message_lower:
                return {"type": "enhance", "parameters": {"type": "upscale_4k"}, "needs_file": True}
            elif '2k' in message_lower:
                return {"type": "enhance", "parameters": {"type": "upscale_2k"}, "needs_file": True}
            else:
                return {"type": "enhance", "parameters": {"type": "enhance"}, "needs_file": True}
        
        elif any(word in message_lower for word in ['ضوضاء', 'noise', 'نظف', 'clean']):
            return {"type": "denoise", "parameters": {"type": "audio_denoise"}, "needs_file": True}
        
        elif any(word in message_lower for word in ['حول', 'convert', 'تحويل']):
            format_type = 'mp4'
            if 'mp3' in message_lower:
                format_type = 'mp3'
            return {"type": "convert", "parameters": {"format": format_type}, "needs_file": True}
        
        else:
            return {"type": "chat", "parameters": {}, "needs_file": False}
    
    def _fallback_response(self, command: str) -> Dict[str, Any]:
        """Fallback response when AI is not available"""
        return {
            "action": "chat",
            "message": "فهمت طلبك! لكن احتاج منك توضيح أكثر أو استخدم الأزرار التفاعلية للوصول السريع لما تريد.\n\n"
                      "💡 يمكنك:\n"
                      "• إرسال ملف فيديو أو صوت\n"
                      "• استخدام أوامر واضحة مثل 'حسن الفيديو' أو 'نظف الصوت'\n"
                      "• الاستعانة بالقائمة الذكية أدناه",
            "needs_file": False,
            "confidence": 0.5,
            "show_main_menu": True
        }