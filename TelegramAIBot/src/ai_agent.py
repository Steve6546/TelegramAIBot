"""
AI Agent using LangChain for natural language understanding
Interprets user commands and selects appropriate tools
"""

import json
import logging
import os
import httpx
from typing import Dict, Any, Optional

from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.schema import BaseOutputParser
from langchain.prompts import PromptTemplate
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIAgent:
    """AI Agent for interpreting user commands and managing tools"""
    
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
            
        self.setup_tools()
        
    def setup_tools(self):
        """Setup LangChain tools from tool manager"""
        self.tools = [
            Tool(
                name="enhance_video",
                description="Enhance video quality using Real-ESRGAN upscaling. Use for requests about improving video quality, resolution, or clarity.",
                func=self.tool_manager.enhance_video
            ),
            Tool(
                name="denoise_audio",
                description="Remove noise from audio or video files using FFmpeg. Use for requests about cleaning audio, removing background noise.",
                func=self.tool_manager.denoise_audio
            ),
            Tool(
                name="convert_format",
                description="Convert media files between different formats using FFmpeg. Use for format conversion requests.",
                func=self.tool_manager.convert_format
            ),
            Tool(
                name="upscale_video",
                description="Upscale video resolution to 2K or 4K using AI. Use for requests about increasing video size or resolution.",
                func=self.tool_manager.upscale_video
            ),
            Tool(
                name="analyze_media",
                description="Analyze media file properties and suggest best enhancement options.",
                func=self.tool_manager.analyze_media
            )
        ]
        
    async def process_command(self, command: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process natural language command and determine appropriate action
        
        Args:
            command: User's natural language command
            user_context: Context about user's files and previous interactions
            
        Returns:
            Dictionary with action type and parameters
        """
        try:
            # Create system prompt for command interpretation
            system_prompt = """
            You are an AI assistant for a media processing bot. Your job is to interpret user commands in Arabic or English and determine the appropriate action.

            Available actions:
            - enhance_video: Improve video quality and resolution
            - denoise_audio: Remove noise from audio/video
            - convert_format: Convert between file formats
            - upscale_video: Increase video resolution to 2K/4K
            - analyze_media: Analyze file and suggest improvements

            User context: The user may have recently uploaded files or have ongoing tasks.

            Respond with JSON in this format:
            {
                "action": "action_name",
                "parameters": {"key": "value"},
                "needs_file": true/false,
                "message": "Response message to user",
                "confidence": 0.8
            }

            If the command is unclear or you need more information, set "action" to null and provide a helpful message.
            """

            # Add user context to the prompt
            context_info = ""
            if user_context:
                if user_context.get('recent_files'):
                    context_info += f"\nUser's recent files: {user_context['recent_files']}"
                if user_context.get('preferred_settings'):
                    context_info += f"\nUser preferences: {user_context['preferred_settings']}"

            user_prompt = f"""
            User command: "{command}"
            {context_info}
            
            Please interpret this command and provide the appropriate action.
            """

            # Try OpenAI first, then Gemini as fallback
            if self.openai_client:
                # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                result = json.loads(response.choices[0].message.content)
            elif self.gemini_client:
                # Use Gemini API
                result = await self._call_gemini_api(system_prompt, user_prompt)
            else:
                raise ValueError("No AI service available. Please provide OPENAI_API_KEY or GOOGLE_API_KEY.")
            
            # Validate response structure
            if not isinstance(result, dict):
                raise ValueError("Invalid response format")
                
            # Set defaults for missing fields
            result.setdefault('needs_file', False)
            result.setdefault('confidence', 0.5)
            result.setdefault('parameters', {})
            
            logger.info(f"AI Agent processed command: {command} -> {result.get('action')}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing command with AI agent: {e}")
            return {
                "action": None,
                "message": "عذراً، لم أتمكن من فهم طلبك. يرجى المحاولة مرة أخرى أو استخدام الأزرار التفاعلية.",
                "needs_file": False,
                "confidence": 0.0
            }
            
    async def suggest_enhancements(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze file and suggest best enhancement options
        
        Args:
            file_info: Information about the media file
            
        Returns:
            Dictionary with suggested enhancements
        """
        try:
            prompt = f"""
            Analyze this media file and suggest the best enhancement options:
            
            File info:
            - Type: {file_info.get('type', 'unknown')}
            - Format: {file_info.get('format', 'unknown')}
            - Duration: {file_info.get('duration', 'unknown')}
            - Resolution: {file_info.get('resolution', 'unknown')}
            - File size: {file_info.get('size', 'unknown')}
            - Audio info: {file_info.get('audio_info', 'unknown')}
            
            Respond with JSON suggesting 2-3 enhancement options with reasons:
            {{
                "suggestions": [
                    {{
                        "type": "enhancement_type",
                        "reason": "why this enhancement is recommended",
                        "priority": "high/medium/low"
                    }}
                ],
                "recommended_sequence": ["step1", "step2", "step3"]
            }}
            """
            
            if self.openai_client:
                # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                return json.loads(response.choices[0].message.content)
            elif self.gemini_client:
                return await self._call_gemini_api("", prompt)
            else:
                raise ValueError("No AI service available")
            
        except Exception as e:
            logger.error(f"Error suggesting enhancements: {e}")
            return {
                "suggestions": [
                    {
                        "type": "general_enhancement",
                        "reason": "تحسين عام للجودة",
                        "priority": "medium"
                    }
                ],
                "recommended_sequence": ["general_enhancement"]
            }
            
    async def explain_process(self, enhancement_type: str, file_info: Dict) -> str:
        """
        Explain what the enhancement process will do
        
        Args:
            enhancement_type: Type of enhancement to explain
            file_info: Information about the file
            
        Returns:
            Human-readable explanation
        """
        try:
            prompt = f"""
            Explain in Arabic what this enhancement process will do to the user's file:
            
            Enhancement type: {enhancement_type}
            File info: {file_info}
            
            Provide a clear, friendly explanation of:
            1. What will be improved
            2. How long it might take
            3. What to expect in the result
            
            Keep it concise and user-friendly.
            """
            
            if self.openai_client:
                # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=200
                )
                return response.choices[0].message.content
            elif self.gemini_client:
                result = await self._call_gemini_api("", prompt)
                return result.get("message", f"سيتم تطبيق تحسين {enhancement_type} على ملفك.")
            else:
                return f"سيتم تطبيق تحسين {enhancement_type} على ملفك."
            
        except Exception as e:
            logger.error(f"Error explaining process: {e}")
            return f"سيتم تطبيق تحسين {enhancement_type} على ملفك."
            
    def get_tool_by_name(self, tool_name: str) -> Optional[Tool]:
        """Get a specific tool by name"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
        
    async def validate_parameters(self, action: str, parameters: Dict) -> Dict[str, Any]:
        """
        Validate and normalize parameters for an action
        
        Args:
            action: The action to perform
            parameters: Parameters for the action
            
        Returns:
            Validated and normalized parameters
        """
        validated = parameters.copy()
        
        if action == "upscale_video":
            # Validate resolution
            resolution = parameters.get('resolution', '2k').lower()
            if resolution not in ['2k', '4k', '1080p', '720p']:
                validated['resolution'] = '2k'
                
        elif action == "convert_format":
            # Validate output format
            format_type = parameters.get('format', 'mp4').lower()
            supported_formats = ['mp4', 'avi', 'mov', 'mkv', 'mp3', 'wav', 'aac']
            if format_type not in supported_formats:
                validated['format'] = 'mp4'
                
        elif action == "denoise_audio":
            # Validate noise reduction level
            level = parameters.get('level', 'medium')
            if level not in ['light', 'medium', 'strong']:
                validated['level'] = 'medium'
                
        return validated
        
    async def _call_gemini_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Call Google Gemini API for AI processing
        
        Args:
            system_prompt: System instruction
            user_prompt: User query
            
        Returns:
            Dictionary with AI response
        """
        try:
            # Combine system and user prompts for Gemini
            combined_prompt = f"{system_prompt}\n\nUser: {user_prompt}\n\nPlease respond with JSON format."
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": combined_prompt
                            }
                        ]
                    }
                ]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.gemini_api_key
            }
            
            response = await self.gemini_client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("candidates", [{}])[0].get("content", {})
                text = content.get("parts", [{}])[0].get("text", "")
                
                # Try to parse as JSON
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # If not JSON, return a default structure
                    return {
                        "action": None,
                        "message": text,
                        "needs_file": False,
                        "confidence": 0.5
                    }
            else:
                raise ValueError(f"Gemini API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return {
                "action": None,
                "message": "عذراً، لم أتمكن من فهم طلبك. يرجى المحاولة مرة أخرى.",
                "needs_file": False,
                "confidence": 0.0
            }
