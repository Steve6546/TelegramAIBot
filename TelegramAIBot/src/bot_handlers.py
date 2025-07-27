"""
Telegram bot handlers for user interactions
Handles commands, messages, and callback queries
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .utils import format_file_size, get_file_extension, is_valid_url
from .storage import StorageManager

logger = logging.getLogger(__name__)

class BotHandlers:
    """Handles all Telegram bot interactions"""
    
    def __init__(self, ai_agent, task_queue, storage: StorageManager, monitor):
        self.ai_agent = ai_agent
        self.task_queue = task_queue
        self.storage = storage
        self.monitor = monitor
        self.start_time = time.time()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = """
🎬 *مرحباً بك في Smart Media AI Assistant*

أنا مساعد ذكي لتحسين جودة الفيديو والصوت باستخدام الذكاء الاصطناعي!

*ما يمكنني فعله:*
• 📈 رفع دقة الفيديو (2K, 4K)
• 🔇 إزالة الضوضاء من الصوت والفيديو
• 🎨 تحسين جودة الصورة والألوان
• 🔄 تحويل صيغ الملفات
• ⚡ معالجة سريعة بتقنية GPU

*كيفية الاستخدام:*
1. أرسل ملف فيديو أو صوت
2. أو أرسل رابط من YouTube/موقع آخر
3. اختر نوع التحسين المطلوب
4. انتظر النتيجة المحسّنة!

استخدم /help للمزيد من المساعدة
استخدم /status لمعرفة حالة النظام
        """
        
        keyboard = [
            [InlineKeyboardButton("📚 دليل الاستخدام", callback_data="help_guide")],
            [InlineKeyboardButton("🔧 أدوات متقدمة", callback_data="advanced_tools")],
            [InlineKeyboardButton("📊 إحصائيات النظام", callback_data="system_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📖 *دليل الاستخدام المفصل*

*الأوامر المتاحة:*
• `/start` - رسالة الترحيب
• `/help` - هذا الدليل
• `/status` - حالة النظام
• `/cancel` - إلغاء المهمة الحالية

*أنواع الملفات المدعومة:*
• فيديو: MP4, AVI, MOV, MKV, WebM
• صوت: MP3, WAV, AAC, FLAC, OGG
• الحد الأقصى: 50 ميجابايت

*خيارات التحسين:*
🎯 *رفع الدقة* - تكبير الفيديو إلى 2K أو 4K
🔇 *إزالة الضوضاء* - تنظيف الصوت من التشويش
🎨 *تحسين الجودة* - تطبيق فلاتر ذكية
🔄 *تحويل الصيغة* - تغيير نوع الملف

*أمثلة على الأوامر الطبيعية:*
• "حسّن جودة هذا الفيديو إلى 4K"
• "أزل الضوضاء من هذا الصوت"
• "حوّل هذا الملف إلى MP4"
• "اجعل الفيديو أوضح وأكثر حدة"
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            stats = await self.monitor.get_system_stats()
            queue_info = await self.task_queue.get_queue_info()
            
            status_text = f"""
📊 *حالة النظام*

*الموارد:*
• المعالج: {stats['cpu_percent']:.1f}%
• الذاكرة: {stats['memory_percent']:.1f}%
• القرص: {stats['disk_percent']:.1f}%
{'• كرت الرسوم: ' + f"{stats['gpu_percent']:.1f}%" if stats.get('gpu_percent') else '• كرت الرسوم: غير متاح'}

*قائمة المهام:*
• المهام النشطة: {queue_info['active_tasks']}
• في الانتظار: {queue_info['pending_tasks']}
• تمت معالجتها اليوم: {queue_info['completed_today']}

*حالة الأدوات:*
• FFmpeg: {'✅ متاح' if stats['tools']['ffmpeg'] else '❌ غير متاح'}
• Real-ESRGAN: {'✅ متاح' if stats['tools']['realesrgan'] else '❌ غير متاح'}
• GPU Acceleration: {'✅ مفعّل' if stats['tools']['gpu'] else '❌ معطّل'}
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="refresh_status")],
                [InlineKeyboardButton("🗑️ تنظيف الملفات المؤقتة", callback_data="cleanup_temp")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                status_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await update.message.reply_text("❌ خطأ في الحصول على حالة النظام")
            
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command"""
        user_id = update.effective_user.id
        cancelled_tasks = await self.task_queue.cancel_user_tasks(user_id)
        
        if cancelled_tasks > 0:
            await update.message.reply_text(f"✅ تم إلغاء {cancelled_tasks} مهمة")
        else:
            await update.message.reply_text("ℹ️ لا توجد مهام نشطة لإلغائها")
            
    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle media files (video, audio, voice)"""
        message = update.message
        user_id = update.effective_user.id
        
        # Get file information
        if message.video:
            file_obj = message.video
            file_type = "video"
        elif message.audio:
            file_obj = message.audio
            file_type = "audio"
        elif message.voice:
            file_obj = message.voice
            file_type = "voice"
        elif message.video_note:
            file_obj = message.video_note
            file_type = "video_note"
        else:
            await message.reply_text("❌ نوع الملف غير مدعوم")
            return
            
        # Check file size
        if file_obj.file_size > 50 * 1024 * 1024:  # 50MB
            await message.reply_text("❌ حجم الملف كبير جداً (الحد الأقصى 50 ميجابايت)")
            return
            
        # Send processing options
        await self.send_processing_options(message, file_obj.file_id, file_type)
        
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (URLs or natural language commands)"""
        text = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Check if it's a URL
        if is_valid_url(text):
            await self.handle_url(update, text)
        else:
            # Process as natural language command
            await self.handle_natural_command(update, text)
            
    async def handle_url(self, update: Update, url: str):
        """Handle URL processing"""
        message = update.message
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            await message.reply_text("❌ رابط غير صحيح")
            return
            
        # Check if it's a supported platform
        supported_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
        if not any(domain in parsed.netloc.lower() for domain in supported_domains):
            await message.reply_text("❌ هذا الموقع غير مدعوم حالياً")
            return
            
        # Send URL processing options
        keyboard = [
            [InlineKeyboardButton("📥 تحميل وتحسين", callback_data=f"download_enhance:{url}")],
            [InlineKeyboardButton("📥 تحميل فقط", callback_data=f"download_only:{url}")],
            [InlineKeyboardButton("ℹ️ معلومات الفيديو", callback_data=f"video_info:{url}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "🔗 *تم اكتشاف رابط*\n\nماذا تريد أن تفعل؟",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def handle_natural_command(self, update: Update, command: str):
        """Handle natural language commands using AI agent"""
        message = update.message
        user_id = update.effective_user.id
        
        # Show typing indicator
        await message.reply_chat_action("typing")
        
        try:
            # Get user's latest file if any
            user_context = await self.storage.get_user_context(user_id)
            
            # Process command with Smart AI agent
            response = await self.ai_agent.process_natural_command(command, user_context)
            
            if response.get('needs_file'):
                await message.reply_text(
                    "📁 *احتاج إلى ملف للمعالجة*\n\n"
                    "يرجى إرسال ملف فيديو أو صوت أولاً، أو إرسال رابط للتحميل.",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif response.get('action') and response.get('action') not in ['greeting', 'help', 'status', 'chat']:
                # Execute the requested action
                await self.execute_ai_action(message, response)
            else:
                # Send the message with smart menu if available
                reply_text = response.get('message', "❓ لم أفهم طلبك. حاول مرة أخرى.")
                
                # Check if we should show smart menus
                if response.get('show_main_menu'):
                    keyboard = [
                        [InlineKeyboardButton("🎬 أدوات الفيديو", callback_data="video_tools")],
                        [InlineKeyboardButton("🎵 أدوات الصوت", callback_data="audio_tools")],
                        [InlineKeyboardButton("🔄 تحويل الصيغ", callback_data="conversion_tools")],
                        [InlineKeyboardButton("🤖 ذكاء اصطناعي", callback_data="ai_tools")],
                        [InlineKeyboardButton("📊 حالة النظام", callback_data="system_stats")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                elif response.get('show_help_menu'):
                    keyboard = [
                        [InlineKeyboardButton("📚 دليل شامل", callback_data="help_guide")],
                        [InlineKeyboardButton("🎬 أدوات متقدمة", callback_data="advanced_tools")],
                        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                elif response.get('show_status_menu'):
                    keyboard = [
                        [InlineKeyboardButton("📊 إحصائيات مفصلة", callback_data="detailed_stats")],
                        [InlineKeyboardButton("⚠️ تنبيهات النظام", callback_data="system_alerts")],
                        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
                else:
                    await message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Error processing natural command: {e}")
            await message.reply_text("❌ خطأ في معالجة الطلب")
            
    async def send_processing_options(self, message, file_id: str, file_type: str):
        """Send processing options for uploaded media"""
        keyboard = [
            [
                InlineKeyboardButton("📈 رفع الدقة 2K", callback_data=f"enhance:upscale_2k:{file_id}"),
                InlineKeyboardButton("📈 رفع الدقة 4K", callback_data=f"enhance:upscale_4k:{file_id}")
            ],
            [
                InlineKeyboardButton("🔇 إزالة الضوضاء", callback_data=f"enhance:denoise:{file_id}"),
                InlineKeyboardButton("🎨 تحسين الجودة", callback_data=f"enhance:enhance:{file_id}")
            ],
            [
                InlineKeyboardButton("🔄 تحويل إلى MP4", callback_data=f"convert:mp4:{file_id}"),
                InlineKeyboardButton("🔄 تحويل إلى MP3", callback_data=f"convert:mp3:{file_id}")
            ],
            [InlineKeyboardButton("🤖 معالجة ذكية", callback_data=f"ai_enhance:{file_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        file_info = f"📎 *تم استلام ملف {file_type}*\n\nاختر نوع المعالجة المطلوبة:"
        
        await message.reply_text(
            file_info,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        try:
            if data.startswith("enhance:"):
                await self.handle_enhancement_callback(query, data)
            elif data.startswith("convert:"):
                await self.handle_conversion_callback(query, data)
            elif data.startswith("ai_enhance:"):
                await self.handle_ai_enhancement_callback(query, data)
            elif data.startswith("download_"):
                await self.handle_download_callback(query, data)
            elif data == "refresh_status":
                await self.refresh_status(query)
            elif data == "cleanup_temp":
                await self.cleanup_temp_files(query)
            elif data == "help_guide":
                await self.show_help_guide(query)
            elif data == "advanced_tools":
                await self.show_advanced_tools(query)
            elif data == "system_stats":
                await self.show_system_stats(query)
            elif data == "main_menu":
                await self.show_main_menu(query)
            elif data == "video_tools":
                await self.show_video_tools(query)
            elif data == "audio_tools":
                await self.show_audio_tools(query)
            elif data == "conversion_tools":
                await self.show_conversion_tools(query)
            elif data == "ai_tools":
                await self.show_ai_tools(query)
            elif data == "advanced_settings":
                await self.show_advanced_settings(query)
            elif data == "performance_monitor":
                await self.show_performance_monitor(query)
            elif data == "detailed_stats":
                await self.show_detailed_stats(query)
            elif data == "system_alerts":
                await self.show_system_alerts(query)
            elif data.startswith("enhance:"):
                enhancement_type = data.split(":", 1)[1]
                await self.handle_enhancement_request(query, enhancement_type)
            elif data.startswith("convert:"):
                target_format = data.split(":", 1)[1]
                await self.handle_conversion_request(query, target_format)
            elif data in ["ai_analyze", "ai_auto_enhance", "ai_suggestions", "ai_natural_commands", "ai_detailed_report", "ai_settings"]:
                await self.handle_ai_tools(query, data)
            elif data in ["set_quality", "gpu_settings", "performance_settings", "system_settings", "storage_settings", "notification_settings"]:
                await self.handle_settings(query, data)
            elif data == "clear_alerts":
                await self.clear_system_alerts(query)
            elif data == "custom_conversion":
                await self.show_custom_conversion(query)
                
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}")
            await query.edit_message_text("❌ خطأ في معالجة الطلب")
            
    async def handle_enhancement_callback(self, query, data: str):
        """Handle enhancement callbacks"""
        _, enhancement_type, file_id = data.split(":", 2)
        user_id = query.from_user.id
        
        # Add task to queue
        task_id = await self.task_queue.add_task(
            user_id=user_id,
            task_type="enhance",
            file_id=file_id,
            parameters={"type": enhancement_type},
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        
        await query.edit_message_text(
            f"⏳ *بدء المعالجة...*\n\n"
            f"معرف المهمة: `{task_id}`\n"
            f"نوع التحسين: {enhancement_type}\n\n"
            f"سيتم إشعارك عند انتهاء المعالجة.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def handle_conversion_callback(self, query, data: str):
        """Handle format conversion callbacks"""
        _, output_format, file_id = data.split(":", 2)
        user_id = query.from_user.id
        
        task_id = await self.task_queue.add_task(
            user_id=user_id,
            task_type="convert",
            file_id=file_id,
            parameters={"format": output_format},
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        
        await query.edit_message_text(
            f"⏳ *بدء التحويل...*\n\n"
            f"معرف المهمة: `{task_id}`\n"
            f"التحويل إلى: {output_format.upper()}\n\n"
            f"سيتم إشعارك عند انتهاء التحويل.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def handle_ai_enhancement_callback(self, query, data: str):
        """Handle AI-powered enhancement"""
        file_id = data.split(":", 1)[1]
        user_id = query.from_user.id
        
        task_id = await self.task_queue.add_task(
            user_id=user_id,
            task_type="ai_enhance",
            file_id=file_id,
            parameters={"auto": True},
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
        
        await query.edit_message_text(
            f"🤖 *بدء المعالجة الذكية...*\n\n"
            f"معرف المهمة: `{task_id}`\n"
            f"سيقوم الذكاء الاصطناعي بتحليل الملف واختيار أفضل طرق التحسين.\n\n"
            f"سيتم إشعارك عند انتهاء المعالجة.",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
            )
            
    async def execute_ai_action(self, message, response):
        """Execute action determined by AI agent"""
        action = response['action']
        parameters = response.get('parameters', {})
        
        if action == 'enhance_video':
            await message.reply_text("🎬 سأقوم بتحسين الفيديو...")
        elif action == 'denoise_audio':
            await message.reply_text("🔇 سأقوم بإزالة الضوضاء من الصوت...")
        elif action == 'convert_format':
            format_type = parameters.get('format', 'MP4')
            await message.reply_text(f"🔄 سأقوم بتحويل الملف إلى {format_type}...")
        else:
            await message.reply_text(response.get('message', "تم فهم طلبك وسيتم تنفيذه قريباً."))
    
    async def show_help_guide(self, query):
        """Show comprehensive help guide"""
        help_text = """
📚 **دليل الاستخدام التفصيلي**

🎯 **الميزات الأساسية:**
• 📈 رفع دقة الفيديو (2K, 4K, 8K)
• 🔇 إزالة الضوضاء من الصوت
• 🎨 تحسين جودة الصورة والألوان
• 🔄 تحويل صيغ الملفات
• ⚡ معالجة سريعة بتقنية GPU

🤖 **الذكاء الاصطناعي:**
• فهم الأوامر الطبيعية
• اختيار الأدوات المناسبة تلقائياً
• تحليل الملفات وتقديم اقتراحات ذكية

🛠️ **الأدوات المتوفرة:**
• FFmpeg - معالجة الصوت والفيديو
• Real-ESRGAN - تحسين الصور بالذكاء الاصطناعي
• Video2X - رفع دقة الفيديو
• أدوات ضغط وتحويل متقدمة

📤 **طرق الاستخدام:**
1. أرسل ملف فيديو/صوت مباشرة
2. أرسل رابط من YouTube أو مواقع أخرى
3. استخدم الأوامر الطبيعية مثل "حسّن هذا الفيديو"
4. اختر من الأزرار المتاحة

⚙️ **الأوامر:**
/start - الترحيب والبداية
/help - هذا الدليل
/status - حالة النظام
/cancel - إلغاء المهام الجارية
/tools - عرض الأدوات المتاحة
"""
        
        keyboard = [
            [InlineKeyboardButton("🔧 أدوات متقدمة", callback_data="advanced_tools")],
            [InlineKeyboardButton("📊 إحصائيات النظام", callback_data="system_stats")],
            [InlineKeyboardButton("🔄 تحديث المعلومات", callback_data="refresh_status")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def show_advanced_tools(self, query):
        """Show advanced tools menu"""
        tools_text = """
🔧 **الأدوات المتقدمة**

🎬 **أدوات الفيديو:**
• تحسين الدقة (2K/4K/8K)
• إزالة الضوضاء
• تحسين الألوان والإضاءة
• ضغط ذكي مع الحفاظ على الجودة

🎵 **أدوات الصوت:**
• إزالة الضوضاء والتشويش
• تحسين جودة الصوت
• تطبيع مستوى الصوت
• تحويل الصيغ

🔄 **تحويل الصيغ:**
• MP4, AVI, MOV, MKV
• MP3, WAV, FLAC, AAC
• تحسين معاملات الضغط

🤖 **ميزات الذكاء الاصطناعي:**
• تحليل تلقائي للملفات
• اقتراح التحسينات المناسبة
• معالجة الأوامر الطبيعية
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎬 أدوات فيديو", callback_data="video_tools"),
                InlineKeyboardButton("🎵 أدوات صوت", callback_data="audio_tools")
            ],
            [
                InlineKeyboardButton("🔄 تحويل صيغ", callback_data="conversion_tools"),
                InlineKeyboardButton("🤖 أدوات AI", callback_data="ai_tools")
            ],
            [
                InlineKeyboardButton("⚙️ إعدادات متقدمة", callback_data="advanced_settings"),
                InlineKeyboardButton("📊 مراقبة الأداء", callback_data="performance_monitor")
            ],
            [InlineKeyboardButton("🔙 العودة", callback_data="help_guide")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            tools_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def show_system_stats(self, query):
        """Show system statistics and status"""
        try:
            # Get system info from monitor
            stats = await self.monitor.get_system_stats()
            tools_status = self.tool_manager.get_tools_status()
            
            stats_text = f"""
📊 **إحصائيات النظام**

💻 **الأداء:**
• استخدام المعالج: {stats.get('cpu_percent', 0):.1f}%
• استخدام الذاكرة: {stats.get('memory_percent', 0):.1f}%
• مساحة القرص المتاحة: {stats.get('disk_free_gb', 0):.1f} GB

🛠️ **حالة الأدوات:**
• FFmpeg: {'✅ متاح' if tools_status.get('ffmpeg') else '❌ غير متاح'}
• Real-ESRGAN: {'✅ متاح' if tools_status.get('realesrgan') else '❌ غير متاح'}
• Video2X: {'✅ متاح' if tools_status.get('video2x') else '❌ غير متاح'}
• GPU: {'✅ متاح' if tools_status.get('gpu') else '❌ غير متاح'}

📈 **الإحصائيات:**
• المهام النشطة: {await self.task_queue.get_active_tasks_count()}
• المهام المكتملة: {await self.task_queue.get_completed_tasks_count()}
• وقت التشغيل: {self._get_uptime()}
• إجمالي الملفات المعالجة: {self._get_total_processed_files()}

🌡️ **حالة النظام:**
• درجة حرارة المعالج: {stats.get('cpu_temp', 'غير متاح')}
• استخدام الشبكة: {stats.get('network_usage', 'عادي')}
• حالة الذاكرة: {'جيدة' if stats.get('memory_percent', 0) < 80 else 'مرتفعة'}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 تحديث", callback_data="refresh_status"),
                    InlineKeyboardButton("🧹 تنظيف الملفات", callback_data="cleanup_temp")
                ],
                [
                    InlineKeyboardButton("📈 إحصائيات متقدمة", callback_data="detailed_stats"),
                    InlineKeyboardButton("⚠️ التنبيهات", callback_data="system_alerts")
                ],
                [InlineKeyboardButton("🔙 العودة", callback_data="help_guide")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error showing system stats: {e}")
            await query.edit_message_text(
                "❌ خطأ في جلب إحصائيات النظام",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="help_guide")
                ]])
            )
    
    async def refresh_status(self, query):
        """Refresh system status"""
        await query.answer("🔄 جاري تحديث البيانات...")
        await self.show_system_stats(query)
        
    async def cleanup_temp_files(self, query):
        """Clean up temporary files"""
        try:
            cleaned_files = await self.storage.cleanup_temp_files()
            await query.answer(f"🧹 تم حذف {cleaned_files} ملف مؤقت")
            await self.show_system_stats(query)
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
            await query.answer("❌ خطأ في تنظيف الملفات")
    
    def _get_uptime(self):
        """Get system uptime"""
        try:
            import time
            uptime_seconds = time.time() - self.start_time
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}س {minutes}د"
        except:
            return "غير متاح"
    
    def _get_total_processed_files(self):
        """Get total processed files count"""
        # This would typically come from a database or file counter
        return "غير متاح"
    
    async def show_main_menu(self, query):
        """Show main menu"""
        await self.start_command(query, None)
        
    async def show_video_tools(self, query):
        """Show video tools submenu"""
        video_text = """
🎬 **أدوات معالجة الفيديو**

📈 **تحسين الدقة:**
• رفع إلى 2K (1440p)
• رفع إلى 4K (2160p)  
• رفع إلى 8K (4320p)
• تحسين ذكي بالذكاء الاصطناعي

🎨 **تحسين الجودة:**
• تحسين الألوان والتباين
• زيادة الحدة والوضوح
• إزالة الضوضاء المرئية
• تصحيح الإضاءة

⚡ **معالجة سريعة:**
• تسريع GPU مدعوم
• معالجة بالدفعات
• ضغط ذكي
• حفظ متقدم للجودة
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📈 رفع دقة 2K", callback_data="enhance:upscale_2k"),
                InlineKeyboardButton("📈 رفع دقة 4K", callback_data="enhance:upscale_4k")
            ],
            [
                InlineKeyboardButton("🎨 تحسين ألوان", callback_data="enhance:color_enhance"),
                InlineKeyboardButton("🔇 إزالة ضوضاء", callback_data="enhance:denoise_video")
            ],
            [
                InlineKeyboardButton("⚡ معالجة سريعة", callback_data="enhance:fast_process"),
                InlineKeyboardButton("🤖 تحسين ذكي", callback_data="ai_enhance")
            ],
            [InlineKeyboardButton("🔙 العودة", callback_data="advanced_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            video_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def show_audio_tools(self, query):
        """Show audio tools submenu"""
        audio_text = """
🎵 **أدوات معالجة الصوت**

🔇 **إزالة الضوضاء:**
• فلترة الضوضاء الخلفية
• إزالة الصدى والتشويش
• تنقية الأصوات
• تحسين وضوح الكلام

🎚️ **تحسين الجودة:**
• تطبيع مستوى الصوت
• تحسين الديناميكية
• توازن الترددات
• ضغط ذكي للصوت

🔄 **التحويل والمعالجة:**
• تحويل بين الصيغ
• تغيير معدل العينة
• تقليل حجم الملف
• استخراج الصوت من الفيديو
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔇 إزالة ضوضاء", callback_data="enhance:audio_denoise"),
                InlineKeyboardButton("🎚️ تطبيع الصوت", callback_data="enhance:audio_normalize")
            ],
            [
                InlineKeyboardButton("🎵 تحسين جودة", callback_data="enhance:audio_enhance"),
                InlineKeyboardButton("📊 توازن ترددات", callback_data="enhance:audio_eq")
            ],
            [
                InlineKeyboardButton("🔄 تحويل صيغة", callback_data="conversion_tools"),
                InlineKeyboardButton("🤖 معالجة ذكية", callback_data="ai_enhance")
            ],
            [InlineKeyboardButton("🔙 العودة", callback_data="advanced_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            audio_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def show_conversion_tools(self, query):
        """Show format conversion tools"""
        conversion_text = """
🔄 **أدوات تحويل الصيغ**

🎬 **صيغ الفيديو:**
• MP4 (الأكثر شيوعاً)
• AVI (جودة عالية)
• MOV (Apple)
• MKV (متقدم)
• WebM (للويب)

🎵 **صيغ الصوت:**
• MP3 (شائع)
• WAV (جودة عالية)
• FLAC (بدون فقدان)
• AAC (محسّن)
• OGG (مفتوح المصدر)

⚙️ **إعدادات متقدمة:**
• جودة قابلة للتخصيص
• حجم ملف محسّن
• سرعة معالجة متقدمة
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎬 إلى MP4", callback_data="convert:mp4"),
                InlineKeyboardButton("🎬 إلى AVI", callback_data="convert:avi")
            ],
            [
                InlineKeyboardButton("🎵 إلى MP3", callback_data="convert:mp3"),
                InlineKeyboardButton("🎵 إلى WAV", callback_data="convert:wav")
            ],
            [
                InlineKeyboardButton("📱 إلى WebM", callback_data="convert:webm"),
                InlineKeyboardButton("🔊 إلى FLAC", callback_data="convert:flac")
            ],
            [
                InlineKeyboardButton("⚙️ إعدادات مخصصة", callback_data="custom_conversion"),
                InlineKeyboardButton("🤖 تحويل ذكي", callback_data="ai_enhance")
            ],
            [InlineKeyboardButton("🔙 العودة", callback_data="advanced_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            conversion_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def show_ai_tools(self, query):
        """Show AI-powered tools"""
        ai_text = """
🤖 **أدوات الذكاء الاصطناعي**

🧠 **التحليل الذكي:**
• تحليل تلقائي للملفات
• اكتشاف أفضل طرق التحسين
• تقييم جودة المحتوى
• اقتراحات مخصصة

⚡ **المعالجة الذكية:**
• تحسين تلقائي شامل
• اختيار الأدوات المناسبة
• تحسين معاملات المعالجة
• نتائج محسّنة بالذكاء الاصطناعي

🎯 **ميزات متقدمة:**
• معالجة الأوامر الطبيعية
• تعلم من تفضيلاتك
• تحسين مستمر للنتائج
• دعم متعدد اللغات (عربي/إنجليزي)
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🧠 تحليل ذكي", callback_data="ai_analyze"),
                InlineKeyboardButton("⚡ تحسين تلقائي", callback_data="ai_auto_enhance")
            ],
            [
                InlineKeyboardButton("🎯 اقتراحات ذكية", callback_data="ai_suggestions"),
                InlineKeyboardButton("🗣️ أوامر طبيعية", callback_data="ai_natural_commands")
            ],
            [
                InlineKeyboardButton("📊 تقرير مفصل", callback_data="ai_detailed_report"),
                InlineKeyboardButton("⚙️ إعدادات AI", callback_data="ai_settings")
            ],
            [InlineKeyboardButton("🔙 العودة", callback_data="advanced_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            ai_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def show_advanced_settings(self, query):
        """Show advanced settings"""
        settings_text = """
⚙️ **الإعدادات المتقدمة**

🎛️ **إعدادات المعالجة:**
• جودة المخرجات (عالية/متوسطة/سريعة)
• استخدام GPU (مفعل/معطل)
• حجم الملفات القصوى
• أولوية المعالجة

📊 **إعدادات الأداء:**
• عدد المهام المتزامنة
• استخدام الذاكرة
• مراقبة الأداء
• تحسين السرعة

🔧 **إعدادات النظام:**
• مجلدات التخزين
• تنظيف تلقائي للملفات
• سجلات النظام
• التنبيهات والإشعارات
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🎛️ جودة المعالجة", callback_data="set_quality"),
                InlineKeyboardButton("⚡ تسريع GPU", callback_data="gpu_settings")
            ],
            [
                InlineKeyboardButton("📊 إدارة الأداء", callback_data="performance_settings"),
                InlineKeyboardButton("🔧 إعدادات النظام", callback_data="system_settings")
            ],
            [
                InlineKeyboardButton("💾 إدارة التخزين", callback_data="storage_settings"),
                InlineKeyboardButton("🔔 الإشعارات", callback_data="notification_settings")
            ],
            [InlineKeyboardButton("🔙 العودة", callback_data="advanced_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def show_performance_monitor(self, query):
        """Show performance monitoring dashboard"""
        await self.show_system_stats(query)
        
    async def show_detailed_stats(self, query):
        """Show detailed system statistics"""
        try:
            stats = await self.monitor.get_detailed_stats()
            
            detailed_text = f"""
📈 **إحصائيات مفصلة**

💻 **المعالج:**
• الاستخدام الحالي: {stats.get('cpu_percent', 0):.1f}%
• المتوسط (5 دقائق): {stats.get('cpu_avg_5min', 0):.1f}%
• عدد النوى: {stats.get('cpu_cores', 'غير متاح')}
• التردد: {stats.get('cpu_freq', 'غير متاح')} MHz

🧠 **الذاكرة:**
• المستخدمة: {stats.get('memory_used_gb', 0):.1f} GB
• المتاحة: {stats.get('memory_free_gb', 0):.1f} GB
• إجمالي: {stats.get('memory_total_gb', 0):.1f} GB
• التخزين المؤقت: {stats.get('memory_cached_gb', 0):.1f} GB

💾 **القرص الصلب:**
• المساحة المستخدمة: {stats.get('disk_used_gb', 0):.1f} GB
• المساحة المتاحة: {stats.get('disk_free_gb', 0):.1f} GB
• سرعة القراءة: {stats.get('disk_read_speed', 'غير متاح')}
• سرعة الكتابة: {stats.get('disk_write_speed', 'غير متاح')}

🌐 **الشبكة:**
• البيانات المرسلة: {stats.get('network_sent_mb', 0):.1f} MB
• البيانات المستقبلة: {stats.get('network_recv_mb', 0):.1f} MB
• سرعة الرفع: {stats.get('upload_speed', 'غير متاح')}
• سرعة التحميل: {stats.get('download_speed', 'غير متاح')}
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 تحديث", callback_data="detailed_stats")],
                [InlineKeyboardButton("🔙 العودة", callback_data="system_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                detailed_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error showing detailed stats: {e}")
            await query.edit_message_text(
                "❌ خطأ في جلب الإحصائيات المفصلة",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="system_stats")
                ]])
            )
            
    async def show_system_alerts(self, query):
        """Show system alerts and warnings"""
        try:
            alerts = await self.monitor.get_current_alerts()
            
            if not alerts:
                alerts_text = """
✅ **حالة النظام ممتازة**

🟢 لا توجد تنبيهات حالياً
🟢 جميع الأنظمة تعمل بشكل طبيعي
🟢 الأداء ضمن المعدلات المثلى
🟢 لا توجد مشاكل تتطلب التدخل

👨‍💻 النظام يعمل بكفاءة عالية!
"""
            else:
                alerts_text = "⚠️ **تنبيهات النظام**\n\n"
                for alert in alerts:
                    severity = alert.get('severity', 'info')
                    icon = "🔴" if severity == "critical" else "🟡" if severity == "warning" else "🔵"
                    alerts_text += f"{icon} {alert.get('message', 'تنبيه غير محدد')}\n"
                    alerts_text += f"   الوقت: {alert.get('timestamp', 'غير محدد')}\n\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 تحديث التنبيهات", callback_data="system_alerts"),
                    InlineKeyboardButton("🧹 مسح التنبيهات", callback_data="clear_alerts")
                ],
                [InlineKeyboardButton("🔙 العودة", callback_data="system_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                alerts_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error showing system alerts: {e}")
            await query.edit_message_text(
                "❌ خطأ في جلب تنبيهات النظام",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="system_stats")
                ]])
            )
    
    async def handle_enhancement_request(self, query, enhancement_type):
        """Handle video/audio enhancement requests"""
        try:
            if not query.message.reply_to_message or not query.message.reply_to_message.document:
                await query.edit_message_text(
                    "📁 **يرجى إرسال ملف فيديو أو صوت أولاً**\n\nأرسل الملف ثم اختر نوع التحسين المطلوب.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 العودة", callback_data="main_menu")
                    ]])
                )
                return
            
            # Create enhancement task
            user_id = query.from_user.id
            chat_id = query.message.chat_id
            file_id = query.message.reply_to_message.document.file_id
            
            task_id = await self.task_queue.add_task(
                user_id=user_id,
                chat_id=chat_id,
                file_id=file_id,
                task_type="enhance",
                parameters={"type": enhancement_type}
            )
            
            await query.edit_message_text(
                f"⚡ **تم إنشاء مهمة التحسين**\n\n"
                f"معرف المهمة: `{task_id}`\n"
                f"نوع التحسين: {enhancement_type}\n"
                f"الحالة: قيد الانتظار\n\n"
                f"سيتم إشعارك عند اكتمال المعالجة!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 متابعة التقدم", callback_data=f"task_status:{task_id}")],
                    [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error handling enhancement request: {e}")
            await query.edit_message_text(
                "❌ حدث خطأ أثناء إنشاء مهمة التحسين",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="main_menu")
                ]])
            )
    
    async def handle_conversion_request(self, query, target_format):
        """Handle format conversion requests"""
        try:
            if not query.message.reply_to_message or not query.message.reply_to_message.document:
                await query.edit_message_text(
                    "📁 **يرجى إرسال ملف أولاً**\n\nأرسل الملف ثم اختر الصيغة المطلوبة.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 العودة", callback_data="conversion_tools")
                    ]])
                )
                return
            
            # Create conversion task
            user_id = query.from_user.id
            chat_id = query.message.chat_id
            file_id = query.message.reply_to_message.document.file_id
            
            task_id = await self.task_queue.add_task(
                user_id=user_id,
                chat_id=chat_id,
                file_id=file_id,
                task_type="convert",
                parameters={"format": target_format}
            )
            
            await query.edit_message_text(
                f"🔄 **تم إنشاء مهمة التحويل**\n\n"
                f"معرف المهمة: `{task_id}`\n"
                f"الصيغة المطلوبة: {target_format}\n"
                f"الحالة: قيد الانتظار\n\n"
                f"سيتم إشعارك عند اكتمال التحويل!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 متابعة التقدم", callback_data=f"task_status:{task_id}")],
                    [InlineKeyboardButton("🔙 العودة", callback_data="conversion_tools")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error handling conversion request: {e}")
            await query.edit_message_text(
                "❌ حدث خطأ أثناء إنشاء مهمة التحويل",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="conversion_tools")
                ]])
            )
    
    async def handle_ai_tools(self, query, tool_type):
        """Handle AI-powered tools"""
        try:
            if tool_type == "ai_analyze":
                await query.edit_message_text(
                    "🧠 **التحليل الذكي**\n\nأرسل ملف فيديو أو صوت للحصول على تحليل ذكي شامل للملف وأفضل طرق تحسينه.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 العودة", callback_data="ai_tools")
                    ]])
                )
            elif tool_type == "ai_auto_enhance":
                await query.edit_message_text(
                    "⚡ **التحسين التلقائي**\n\nأرسل ملف وسيقوم الذكاء الاصطناعي بتحليله واختيار أفضل طرق التحسين تلقائياً.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 العودة", callback_data="ai_tools")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "🔧 **هذه الميزة قيد التطوير**\n\nستكون متاحة قريباً!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 العودة", callback_data="ai_tools")
                    ]])
                )
                
        except Exception as e:
            logger.error(f"Error handling AI tools: {e}")
            await query.edit_message_text(
                "❌ حدث خطأ في أدوات الذكاء الاصطناعي",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="ai_tools")
                ]])
            )
    
    async def handle_settings(self, query, setting_type):
        """Handle settings configuration"""
        try:
            settings_text = {
                "set_quality": "🎛️ **إعدادات الجودة**\n\nاختر مستوى الجودة للمعالجة:",
                "gpu_settings": "⚡ **إعدادات التسريع**\n\nإدارة استخدام معالج الرسوميات:",
                "performance_settings": "📊 **إعدادات الأداء**\n\nتحسين أداء المعالجة:",
                "system_settings": "🔧 **إعدادات النظام**\n\nإعدادات عامة للنظام:",
                "storage_settings": "💾 **إدارة التخزين**\n\nإعدادات مساحة التخزين:",
                "notification_settings": "🔔 **إعدادات الإشعارات**\n\nتحديد أنواع الإشعارات:"
            }
            
            await query.edit_message_text(
                settings_text.get(setting_type, "⚙️ **الإعدادات**\n\nهذا القسم قيد التطوير"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="advanced_settings")
                ]])
            )
            
        except Exception as e:
            logger.error(f"Error handling settings: {e}")
            await query.edit_message_text(
                "❌ حدث خطأ في الإعدادات",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="advanced_settings")
                ]])
            )
    
    async def clear_system_alerts(self, query):
        """Clear system alerts"""
        try:
            # Clear alerts in monitor
            self.monitor.alerts.clear()
            
            await query.edit_message_text(
                "✅ **تم مسح جميع التنبيهات**\n\nتم حذف جميع تنبيهات النظام بنجاح.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="system_alerts")
                ]])
            )
            
        except Exception as e:
            logger.error(f"Error clearing alerts: {e}")
            await query.edit_message_text(
                "❌ حدث خطأ أثناء مسح التنبيهات",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 العودة", callback_data="system_alerts")
                ]])
            )
