# Smart Media AI Assistant

## Overview

Smart Media AI Assistant is a Telegram bot that leverages AI to enhance video and audio quality using open-source tools. The system combines natural language processing with powerful media enhancement tools like FFmpeg and Real-ESRGAN to provide an intelligent, user-friendly interface for media processing tasks.

The bot supports multiple enhancement operations including video upscaling to 2K/4K, audio noise reduction, format conversion, and quality improvements, all accessible through natural language commands in both Arabic and English.

## User Preferences

Preferred communication style: Simple, everyday language.
AI Service Support: Both OpenAI GPT-4 and Google Gemini 2.0 Flash APIs supported with automatic fallback.

## Recent Changes (July 27, 2025)

✓ Fixed all dependency installation issues (yt-dlp, httpx, python-telegram-bot)
✓ Updated AI agent to support both OpenAI and Google Gemini APIs with automatic fallback
✓ Installed FFmpeg system dependency for media processing
✓ Resolved all import errors and LSP diagnostics
✓ Successfully deployed bot with proper environment variable configuration
✓ Bot now running and polling for Telegram messages
✓ **Implemented comprehensive Smart AI Daemon (SAD) architecture**
✓ **Added complete inline keyboard system with nested smart buttons**
✓ **Full Arabic/English language support with comprehensive emoji usage**
✓ **All callback handlers implemented for seamless menu navigation**
✓ **Enhanced system monitoring with detailed performance statistics**
✓ **Complete file management system supporting all media types**
✓ **Task queue system with real-time progress tracking**
✓ **Natural language command processing capabilities**

### **🚀 Major System Enhancement (July 27, 2025 - Final Update)**
✓ **RESOLVED JSON Response Issue:** Created enhanced Smart AI Agent that responds naturally instead of JSON
✓ **Natural Conversation Flow:** Bot now understands and responds to Arabic/English greetings and commands naturally
✓ **Intelligent Command Processing:** Direct processing of simple commands without AI overhead
✓ **Smart Menu Integration:** Context-aware button menus based on user interaction type
✓ **Comprehensive Project Documentation:** Complete PROJECT_MAP.md with detailed system architecture
✓ **Zero File Storage in Project:** All media processing happens via Telegram without storing files locally
✓ **Full Operational Status:** Bot working perfectly with all features functional and tested

## System Architecture

The application follows a modular, event-driven architecture built around a Telegram bot interface with AI agent orchestration:

### Core Components
- **Bot Interface Layer**: Handles Telegram interactions through handlers
- **AI Agent**: Uses LangChain and OpenAI GPT-4 for natural language understanding
- **Tool Manager**: Orchestrates media processing tools (FFmpeg, Real-ESRGAN, Video2X)
- **Task Queue**: Manages asynchronous processing with progress tracking
- **Storage Manager**: Handles file operations and cleanup
- **System Monitor**: Tracks resource usage and system health

### Technology Stack
- **Runtime**: Python 3.8+ with asyncio for concurrent operations
- **Bot Framework**: python-telegram-bot for Telegram integration
- **AI Framework**: LangChain with OpenAI API for natural language processing
- **Media Processing**: FFmpeg, Real-ESRGAN, Video2X for enhancement operations
- **File Storage**: Local filesystem with organized directory structure

## Key Components

### 1. Main Application (`main.py`)
Central orchestrator that initializes all components and manages the bot lifecycle. Loads configuration from environment variables or config files and coordinates between different subsystems.

### 2. Bot Handlers (`bot_handlers.py`)
Manages all Telegram interactions including:
- Command handlers (/start, /help)
- Message handlers for files and URLs
- Callback query handlers for interactive buttons
- Progress updates and notifications

### 3. AI Agent (`ai_agent.py`)
Implements LangChain-based AI agent that:
- Interprets user commands in natural language
- Selects appropriate tools based on user intent
- Manages context and conversation state
- Provides intelligent enhancement suggestions

### 4. Tool Manager (`tool_manager.py`)
Orchestrates media processing tools:
- **FFmpeg Tool**: Format conversion, audio denoising, general processing
- **Real-ESRGAN Tool**: AI-powered video upscaling and enhancement
- **Video2X Tool**: Alternative upscaling solution
- Tool availability checking and GPU acceleration detection

### 5. Task Queue (`task_queue.py`)
Asynchronous task management system:
- Background processing with progress tracking
- Task status management (pending, running, completed, failed)
- User notifications and real-time updates
- Resource-aware task scheduling

### 6. Storage Manager (`storage.py`)
File management and organization:
- Temporary file handling with automatic cleanup
- User context persistence
- File registry and metadata tracking
- Directory structure organization

### 7. System Monitor (`monitor.py`)
Resource monitoring and alerting:
- CPU, GPU, and memory usage tracking
- Performance metrics collection
- System health alerts
- Resource usage optimization

## Data Flow

1. **User Input**: User sends message/file to Telegram bot
2. **Command Processing**: Bot handlers interpret the input and user intent
3. **AI Analysis**: AI Agent processes natural language and selects appropriate tools
4. **Task Creation**: Task queue creates background processing job
5. **Tool Execution**: Tool manager executes selected enhancement operations
6. **Progress Tracking**: Real-time updates sent to user via Telegram
7. **Result Delivery**: Enhanced media delivered back to user
8. **Cleanup**: Temporary files cleaned up automatically

## External Dependencies

### Required APIs
- **Telegram Bot API**: For bot interactions and file transfers
- **OpenAI API**: For GPT-4 natural language processing

### System Dependencies
- **FFmpeg**: Core media processing (format conversion, audio processing)
- **Real-ESRGAN**: AI-powered video upscaling (optional but recommended)
- **Video2X**: Alternative upscaling solution (fallback)
- **GPU Drivers**: NVIDIA/CUDA for GPU acceleration (optional)

### Python Dependencies
- **python-telegram-bot**: Telegram bot framework
- **langchain**: AI agent framework
- **openai**: OpenAI API client
- **psutil**: System monitoring
- **pathlib**: File system operations

## Deployment Strategy

### Environment Setup
The application is designed for flexible deployment with environment-based configuration:

1. **Configuration Management**: Uses environment variables with fallback to config.json
2. **Directory Structure**: Automatically creates required directories (downloads, temp, media, logs)
3. **Dependency Checking**: Validates Python version and required environment variables on startup

### Required Environment Variables
- `TELEGRAM_BOT_TOKEN`: Telegram bot authentication token
- `OPENAI_API_KEY`: OpenAI API key for AI agent functionality

### Resource Requirements
- **CPU**: Multi-core recommended for concurrent processing
- **Memory**: 4GB+ RAM for media processing operations
- **Storage**: Adequate space for temporary files and processed media
- **GPU**: Optional but recommended for Real-ESRGAN acceleration

### Scalability Considerations
- Modular architecture allows easy addition of new tools
- Task queue system supports concurrent processing
- Resource monitoring enables load balancing
- File cleanup prevents storage accumulation

The system is architected to be both powerful for advanced users and accessible through natural language interactions, making professional-grade media enhancement tools available to general users through a familiar Telegram interface.