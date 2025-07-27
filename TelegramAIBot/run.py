#!/usr/bin/env python3
"""
Smart Media AI Assistant - Application Runner
Sets up environment and starts the Telegram bot
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

def setup_environment():
    """Setup environment and dependencies"""
    print("🚀 Smart Media AI Assistant")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check required environment variables
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    openai_key = os.getenv('OPENAI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    missing_vars = []
    
    if not telegram_token:
        missing_vars.append('TELEGRAM_BOT_TOKEN')
    
    if not openai_key and not google_key:
        missing_vars.append('OPENAI_API_KEY or GOOGLE_API_KEY')
    
    if missing_vars:
        print("\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these environment variables or add them to a .env file")
        print("You can copy config.json.example to config.json and add your keys there")
        sys.exit(1)
    
    print("✅ Environment variables configured")
    
    # Check directories
    directories = ['downloads', 'temp', 'media', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directory: {directory}")
    
    return True

def check_system_tools():
    """Check availability of system tools"""
    print("\n🔧 Checking system tools...")
    
    tools_status = {}
    
    # Check FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        tools_status['ffmpeg'] = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        tools_status['ffmpeg'] = False
    
    # Check Real-ESRGAN
    realesrgan_names = ['realesrgan-ncnn-vulkan', 'Real-ESRGAN', 'realesrgan']
    tools_status['realesrgan'] = False
    
    for exe_name in realesrgan_names:
        try:
            result = subprocess.run([exe_name, '-h'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                tools_status['realesrgan'] = True
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    # Check GPU
    try:
        result = subprocess.run(['nvidia-smi'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        tools_status['gpu'] = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        tools_status['gpu'] = False
    
    # Display results
    for tool, available in tools_status.items():
        status = "✅" if available else "❌"
        print(f"{status} {tool.upper()}: {'Available' if available else 'Not available'}")
    
    # Warnings for missing tools
    if not tools_status['ffmpeg']:
        print("\n⚠️  Warning: FFmpeg is required for basic functionality")
        print("   Install: sudo apt-get install ffmpeg")
    
    if not tools_status['realesrgan']:
        print("\n⚠️  Warning: Real-ESRGAN not found - AI upscaling will be limited")
        print("   Install from: https://github.com/xinntao/Real-ESRGAN")
    
    if not tools_status['gpu']:
        print("\n⚠️  Info: No GPU detected - processing will use CPU only")
    
    return tools_status

def setup_logging():
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set library log levels
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

def print_startup_info():
    """Print startup information"""
    print("\n" + "=" * 50)
    print("🤖 Smart Media AI Assistant")
    print("   Telegram Bot for Video/Audio Enhancement")
    print("=" * 50)
    
    print("\n📋 Features:")
    print("   • AI-powered video upscaling (Real-ESRGAN)")
    print("   • Audio noise reduction (FFmpeg)")
    print("   • Format conversion")
    print("   • Natural language processing")
    print("   • Progress tracking")
    print("   • System monitoring")
    
    print("\n🌐 Supported Platforms:")
    print("   • YouTube, Vimeo, Dailymotion")
    print("   • Direct file uploads")
    print("   • Various video/audio formats")
    
    print("\n💾 Storage:")
    print("   • Downloads: ./downloads/")
    print("   • Temporary: ./temp/")
    print("   • Processed: ./media/")
    print("   • Logs: ./logs/")
    
    print("\n🔧 Commands:")
    print("   • /start - Welcome message")
    print("   • /help - Usage instructions")
    print("   • /status - System status")
    print("   • /cancel - Cancel tasks")
    
    print("\n" + "=" * 50)
    print("🚀 Starting bot...")
    print("   Press Ctrl+C to stop")
    print("=" * 50)

async def main():
    """Main application entry point"""
    try:
        # Setup environment
        if not setup_environment():
            sys.exit(1)
        
        # Check system tools
        tools_status = check_system_tools()
        
        # Setup logging
        setup_logging()
        
        # Print startup info
        print_startup_info()
        
        # Import and start the bot
        from main import SmartMediaBot
        
        bot = SmartMediaBot()
        await bot.start_bot()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

def check_dependencies():
    """Check if required Python packages are available"""
    required_packages = [
        'telegram',
        'openai', 
        'psutil',
        'yt_dlp',
        'pathlib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required Python packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

if __name__ == "__main__":
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Run the main application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
