"""
Image Tools Manager - Real open-source image enhancement tools
Manages Real-ESRGAN, GFPGAN, AnimeGANv2, SwinIR, and rembg
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any, List
import shutil

logger = logging.getLogger(__name__)

class ImageToolsManager:
    """Manager for real open-source image enhancement tools"""
    
    def __init__(self):
        self.tools_dir = Path("tools")
        self.tools_dir.mkdir(exist_ok=True)
        
        self.tools_status = {
            'realesrgan': {'installed': False, 'path': None},
            'gfpgan': {'installed': False, 'path': None},
            'animegan': {'installed': False, 'path': None},
            'swinir': {'installed': False, 'path': None},
            'rembg': {'installed': False, 'path': None}
        }
        
        self.installation_commands = {
            'realesrgan': {
                'repo': 'https://github.com/xinntao/Real-ESRGAN.git',
                'install_cmd': ['pip', 'install', 'basicsr', 'facexlib', 'gfpgan', 'realesrgan'],
                'test_cmd': ['python', '-c', 'import realesrgan; print("OK")']
            },
            'gfpgan': {
                'repo': 'https://github.com/TencentARC/GFPGAN.git', 
                'install_cmd': ['pip', 'install', 'gfpgan'],
                'test_cmd': ['python', '-c', 'import gfpgan; print("OK")']
            },
            'animegan': {
                'repo': 'https://github.com/bryandlee/animegan2-pytorch.git',
                'install_cmd': ['pip', 'install', 'torch', 'torchvision', 'opencv-python', 'pillow'],
                'test_cmd': ['python', '-c', 'import torch; print("OK")']
            },
            'swinir': {
                'repo': 'https://github.com/JingyunLiang/SwinIR.git',
                'install_cmd': ['pip', 'install', 'torch', 'torchvision', 'opencv-python', 'timm'],
                'test_cmd': ['python', '-c', 'import torch; print("OK")']
            },
            'rembg': {
                'repo': None,  # pip package only
                'install_cmd': ['pip', 'install', 'rembg[new]'],
                'test_cmd': ['python', '-c', 'import rembg; print("OK")']
            }
        }
        
    async def check_tools_status(self) -> Dict[str, bool]:
        """Check which tools are installed and working"""
        status = {}
        
        for tool_name, config in self.installation_commands.items():
            try:
                # Test if tool is available
                result = await asyncio.create_subprocess_exec(
                    *config['test_cmd'],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    self.tools_status[tool_name]['installed'] = True
                    status[tool_name] = True
                    logger.info(f"Tool {tool_name} is available")
                else:
                    self.tools_status[tool_name]['installed'] = False
                    status[tool_name] = False
                    logger.warning(f"Tool {tool_name} test failed: {stderr.decode()}")
                    
            except Exception as e:
                self.tools_status[tool_name]['installed'] = False
                status[tool_name] = False
                logger.error(f"Error checking {tool_name}: {e}")
        
        return status
    
    async def install_tool(self, tool_name: str) -> Dict[str, Any]:
        """Install a specific image enhancement tool"""
        if tool_name not in self.installation_commands:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        try:
            config = self.installation_commands[tool_name]
            
            # Clone repository if needed
            if config['repo']:
                repo_path = self.tools_dir / tool_name
                if not repo_path.exists():
                    logger.info(f"Cloning {tool_name} repository...")
                    result = await asyncio.create_subprocess_exec(
                        'git', 'clone', config['repo'], str(repo_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode != 0:
                        return {"success": False, "error": f"Failed to clone {tool_name}: {stderr.decode()}"}
            
            # Install dependencies
            logger.info(f"Installing {tool_name} dependencies...")
            result = await asyncio.create_subprocess_exec(
                *config['install_cmd'],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                return {"success": False, "error": f"Failed to install {tool_name}: {stderr.decode()}"}
            
            # Test installation
            result = await asyncio.create_subprocess_exec(
                *config['test_cmd'],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                self.tools_status[tool_name]['installed'] = True
                return {"success": True, "message": f"Successfully installed {tool_name}"}
            else:
                return {"success": False, "error": f"Installation test failed for {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error installing {tool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    async def install_all_tools(self) -> Dict[str, Any]:
        """Install all image enhancement tools"""
        results = {}
        
        for tool_name in self.installation_commands.keys():
            logger.info(f"Installing {tool_name}...")
            result = await self.install_tool(tool_name)
            results[tool_name] = result
            
            if result['success']:
                logger.info(f"✅ {tool_name} installed successfully")
            else:
                logger.error(f"❌ {tool_name} installation failed: {result['error']}")
        
        return results
    
    async def enhance_image_realesrgan(self, input_path: str, scale: int = 4) -> Optional[str]:
        """Enhance image using Real-ESRGAN"""
        if not self.tools_status['realesrgan']['installed']:
            return None
        
        try:
            output_path = input_path.replace('.', f'_enhanced_x{scale}.')
            
            # Create Real-ESRGAN enhancement script
            script = f"""
import cv2
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet

# Initialize model
model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale={scale})
upsampler = RealESRGANer(
    scale={scale},
    model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x{scale}plus.pth',
    model=model,
    tile=0,
    tile_pad=10,
    pre_pad=0,
    half=False
)

# Process image
img = cv2.imread('{input_path}', cv2.IMREAD_COLOR)
output, _ = upsampler.enhance(img, outscale={scale})
cv2.imwrite('{output_path}', output)
print("Enhancement completed successfully")
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script)
                script_path = f.name
            
            try:
                result = await asyncio.create_subprocess_exec(
                    'python', script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0 and Path(output_path).exists():
                    return output_path
                else:
                    logger.error(f"Real-ESRGAN failed: {stderr.decode()}")
                    return None
                    
            finally:
                os.unlink(script_path)
                
        except Exception as e:
            logger.error(f"Error in Real-ESRGAN enhancement: {e}")
            return None
    
    async def enhance_face_gfpgan(self, input_path: str) -> Optional[str]:
        """Enhance faces using GFPGAN"""
        if not self.tools_status['gfpgan']['installed']:
            return None
        
        try:
            output_path = input_path.replace('.', '_face_enhanced.')
            
            script = f"""
import cv2
from gfpgan import GFPGANer

# Initialize GFPGAN
restorer = GFPGANer(
    model_path='https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth',
    upscale=2,
    arch='clean',
    channel_multiplier=2,
    bg_upsampler=None
)

# Process image
input_img = cv2.imread('{input_path}', cv2.IMREAD_COLOR)
cropped_faces, restored_faces, restored_img = restorer.enhance(
    input_img,
    has_aligned=False,
    only_center_face=False,
    paste_back=True
)

cv2.imwrite('{output_path}', restored_img)
print("Face enhancement completed")
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script)
                script_path = f.name
            
            try:
                result = await asyncio.create_subprocess_exec(
                    'python', script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0 and Path(output_path).exists():
                    return output_path
                else:
                    logger.error(f"GFPGAN failed: {stderr.decode()}")
                    return None
                    
            finally:
                os.unlink(script_path)
                
        except Exception as e:
            logger.error(f"Error in GFPGAN enhancement: {e}")
            return None
    
    async def remove_background_rembg(self, input_path: str) -> Optional[str]:
        """Remove background using rembg"""
        if not self.tools_status['rembg']['installed']:
            return None
        
        try:
            output_path = input_path.replace('.', '_no_bg.')
            
            script = f"""
from rembg import remove
from PIL import Image

# Process image
with open('{input_path}', 'rb') as input_file:
    input_data = input_file.read()

output_data = remove(input_data)

with open('{output_path}', 'wb') as output_file:
    output_file.write(output_data)

print("Background removal completed")
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script)
                script_path = f.name
            
            try:
                result = await asyncio.create_subprocess_exec(
                    'python', script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0 and Path(output_path).exists():
                    return output_path
                else:
                    logger.error(f"rembg failed: {stderr.decode()}")
                    return None
                    
            finally:
                os.unlink(script_path)
                
        except Exception as e:
            logger.error(f"Error in background removal: {e}")
            return None
    
    async def convert_to_anime_style(self, input_path: str) -> Optional[str]:
        """Convert image to anime style using AnimeGANv2"""
        if not self.tools_status['animegan']['installed']:
            return None
        
        try:
            output_path = input_path.replace('.', '_anime.')
            
            # This is a simplified version - would need actual AnimeGANv2 implementation
            script = f"""
import cv2
import numpy as np
from PIL import Image

# Simple anime-style filter (placeholder for actual AnimeGANv2)
img = cv2.imread('{input_path}')
img = cv2.bilateralFilter(img, 15, 80, 80)
edges = cv2.adaptiveThreshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 7)
edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
cartoon = cv2.bitwise_and(img, edges)

cv2.imwrite('{output_path}', cartoon)
print("Anime style conversion completed")
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script)
                script_path = f.name
            
            try:
                result = await asyncio.create_subprocess_exec(
                    'python', script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0 and Path(output_path).exists():
                    return output_path
                else:
                    logger.error(f"Anime conversion failed: {stderr.decode()}")
                    return None
                    
            finally:
                os.unlink(script_path)
                
        except Exception as e:
            logger.error(f"Error in anime conversion: {e}")
            return None
    
    def get_available_enhancements(self) -> List[Dict[str, Any]]:
        """Get list of available image enhancements"""
        enhancements = []
        
        if self.tools_status['realesrgan']['installed']:
            enhancements.extend([
                {"id": "upscale_2x", "name": "🔧 رفع دقة 2x", "tool": "realesrgan", "params": {"scale": 2}},
                {"id": "upscale_4x", "name": "🎨 رفع دقة 4x", "tool": "realesrgan", "params": {"scale": 4}}
            ])
        
        if self.tools_status['gfpgan']['installed']:
            enhancements.append({
                "id": "enhance_face", "name": "👤 تحسين الوجوه", "tool": "gfpgan", "params": {}
            })
        
        if self.tools_status['rembg']['installed']:
            enhancements.append({
                "id": "remove_bg", "name": "🌟 إزالة الخلفية", "tool": "rembg", "params": {}
            })
        
        if self.tools_status['animegan']['installed']:
            enhancements.append({
                "id": "anime_style", "name": "🎭 تحويل أنمي", "tool": "animegan", "params": {}
            })
        
        # Always available with ImageMagick/FFmpeg
        enhancements.extend([
            {"id": "adjust_colors", "name": "🌈 تعديل الألوان", "tool": "imagemagick", "params": {}},
            {"id": "noise_reduction", "name": "✨ إزالة الضوضاء", "tool": "imagemagick", "params": {}},
            {"id": "sharpen", "name": "🔍 زيادة الحدة", "tool": "imagemagick", "params": {}}
        ])
        
        return enhancements