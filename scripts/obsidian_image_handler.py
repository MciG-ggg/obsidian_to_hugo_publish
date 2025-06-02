#!/usr/bin/env python3
# Obsidian图片处理工具
# 用于处理Obsidian的图片语法并转换为Hugo兼容的格式

import re
import os
from pathlib import Path
import shutil
from typing import Optional
from scripts.config_manager import Config

def process_obsidian_images(content: str, source_file: Path, target_dir: Path, source_dir: Optional[Path] = None) -> str:
    """
    处理Markdown内容中的Obsidian图片链接
    :param content: Markdown内容
    :param source_file: 源Markdown文件路径
    :param target_dir: Hugo文章目录路径
    :param source_dir: 图片源目录
    :return: 处理后的内容
    """
    config = Config()
    
    def find_image(image_name: str) -> Optional[Path]:
        """查找图片文件"""
        # 1. 从配置的图片源目录查找
        image_source_dir = Path(config.get('paths.obsidian.images')).expanduser()
        if (image_source_dir / image_name).exists():
            return image_source_dir / image_name
        
        # 2. 从markdown文件所在目录查找
        if (source_file.parent / image_name).exists():
            return source_file.parent / image_name
            
        # 3. 从指定的源目录查找
        if source_dir and (source_dir / image_name).exists():
            return source_dir / image_name
        
        return None

    def copy_image(image_path: Path) -> Optional[str]:
        """复制图片到文章目录（同级）并返回新的文件名"""
        if not image_path.exists():
            return None
            
        # 使用原始文件名，将空格替换为短横线
        new_name = image_path.stem.replace(' ', '-') + image_path.suffix
        dest_path = target_dir / new_name
        
        # 确保目标目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制图片
        shutil.copy2(image_path, dest_path)
        return new_name

    def process_image_link(match) -> str:
        """处理单个图片链接"""
        if match.group(0).startswith('![['):  # Obsidian格式 ![[image.png]]
            image_name = match.group(1)
            alt_text = image_name.split('/')[-1]  # 使用文件名作为alt文本
        else:  # Markdown格式 ![alt](image.png)
            alt_text = match.group(1) or ''
            image_name = match.group(2)

        # 清理图片名称
        image_name = image_name.split('#')[0].split('?')[0].replace('%20', ' ')
        
        # 查找并复制图片
        image_path = find_image(image_name)
        if not image_path:
            print(f"警告: 找不到图片 {image_name}")
            return match.group(0)
            
        new_name = copy_image(image_path)
        if not new_name:
            print(f"警告: 无法复制图片 {image_name}")
            return match.group(0)
            
        # 返回标准Markdown格式的图片链接，图片和文章同级
        return f"![{alt_text}]({new_name})"

    # 处理两种格式的图片链接
    content = re.sub(r'!\[\[(.*?)\]\]', process_image_link, content)  # Obsidian格式
    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', process_image_link, content)  # Markdown格式

    return content
