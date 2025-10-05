#!/usr/bin/env python3
# Obsidian图片处理工具
# 用于处理Obsidian的图片语法并转换为Hugo兼容的格式

import re
import os
from pathlib import Path
import shutil
from typing import Optional, List, Tuple
from src.core.config_manager import Config
from src.utils.parallel import parallel_process


def find_image(image_name: str, source_file: Path, source_dir: Optional[Path] = None) -> Optional[Path]:
    """查找图片文件"""
    config = Config()
    
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


def copy_image(image_path: Path, target_dir: Path) -> Optional[str]:
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


def process_single_image(args: Tuple[str, str, Path, Path, Optional[Path]]) -> str:
    """
    处理单个图片链接
    :param args: (原匹配内容, 图片名称, alt文本, 源文件路径, 源目录路径)
    """
    original, image_name, alt_text, source_file, source_dir = args
    
    # 清理图片名称
    image_name = image_name.split('#')[0].split('?')[0].replace('%20', ' ').replace('-', ' ')
    
    # 查找并复制图片
    image_path = find_image(image_name, source_file, source_dir)
    if not image_path:
        print(f"警告: 找不到图片 {image_name}")
        return original
        
    # 获取目标目录
    target_dir = source_file.parent / "images"  # 创建images子目录来存放图片
    
    new_name = copy_image(image_path, target_dir)
    if not new_name:
        print(f"警告: 无法复制图片 {image_name}")
        return original
        
    # 返回标准Markdown格式的图片链接
    return f"![{alt_text}]({new_name})"


def process_obsidian_images(content: str, source_file: Path, target_dir: Path, source_dir: Optional[Path] = None) -> str:
    """
    处理Markdown内容中的Obsidian图片链接
    :param content: Markdown内容
    :param source_file: 源Markdown文件路径
    :param target_dir: Hugo文章目录路径
    :param source_dir: 图片源目录
    :return: 处理后的内容
    """
    
    # 提取所有图片链接
    image_matches = []
    
    # 匹配Obsidian格式 ![[image.png]]
    obsidian_pattern = r'!\[\[(.*?)\]\]'
    for match in re.finditer(obsidian_pattern, content):
        image_name = match.group(1)
        alt_text = image_name.split('/')[-1]  # 使用文件名作为alt文本
        image_matches.append((match.group(0), image_name, alt_text, source_file, source_dir))
    
    # 匹配Markdown格式 ![alt](image.png)
    md_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    for match in re.finditer(md_pattern, content):
        alt_text = match.group(1) or ''
        image_name = match.group(2)
        image_matches.append((match.group(0), image_name, alt_text, source_file, source_dir))
    
    # 并行处理所有图片
    if image_matches:
        processed_results = parallel_process(image_matches, process_single_image, max_workers=4)
        
        # 替换原内容中的图片链接
        for i, (original, image_name, alt_text, _, _) in enumerate(image_matches):
            content = content.replace(original, processed_results[i], 1)
    
    return content