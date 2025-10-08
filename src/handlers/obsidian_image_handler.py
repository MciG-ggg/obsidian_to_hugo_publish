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
    
    # 定义可能的文件名变体
    possible_names = [image_name]
    
    # 如果名称包含空格，也尝试连字符变体
    if ' ' in image_name:
        possible_names.append(image_name.replace(' ', '-'))
    # 如果名称包含连字符，也尝试空格变体
    elif '-' in image_name:
        possible_names.append(image_name.replace('-', ' '))
    
    # 1. 在配置的图片源目录查找所有可能的变体
    image_source_dir = Path(config.get('paths.obsidian.images')).expanduser()
    for name in possible_names:
        image_path = image_source_dir / name
        if image_path.exists():
            print(f"在配置的图片目录中找到图片: {image_path}")
            return image_path
    
    # 2. 在markdown文件所在目录查找所有可能的变体
    for name in possible_names:
        image_path = source_file.parent / name
        if image_path.exists():
            print(f"在源文件目录中找到图片: {image_path}")
            return image_path
        
    # 3. 在指定的源目录查找所有可能的变体
    if source_dir:
        for name in possible_names:
            image_path = source_dir / name
            if image_path.exists():
                print(f"在指定源目录中找到图片: {image_path}")
                return image_path
    
    return None


def copy_image(image_path: Path, target_dir: Path) -> Optional[str]:
    """复制图片到文章目录（同级）并返回新的文件名"""
    if not image_path.exists():
        return None
        
    # 使用原始文件名，但替换可能引起问题的字符（如空格）
    # 保留文件名中的原始格式，但将空格替换为连字符以确保URL安全
    original_name = image_path.name
    safe_name = original_name.replace(' ', '-')  # 将空格替换为连字符
    
    dest_path = target_dir / safe_name
    
    # 确保目标目录存在
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制图片
    shutil.copy2(image_path, dest_path)
    print(f"已复制图片从 {image_path} 到 {dest_path}")
    return safe_name


def process_single_image_with_target_dir(args: Tuple[str, str, Path, Path, Path, Optional[Path]]) -> str:
    """
    处理单个图片链接
    :param args: (原匹配内容, 图片名称, alt文本, 源文件路径, 目标目录路径, 源目录路径)
    """
    original, image_name, alt_text, source_file, target_dir, source_dir = args
    
    # 保留原始图片名称用于查找
    original_image_name = image_name
    # 清理图片名称用于查找（移除URL参数等）
    clean_image_name = image_name.split('#')[0].split('?')[0]
    
    print(f"正在处理图片: 原始名称={original_image_name}, 清理后名称={clean_image_name}, 目标目录={target_dir}")
    
    # 首先尝试使用清理后的名称进行查找
    image_path = find_image(clean_image_name, source_file, source_dir)
    
    # 如果没找到，尝试不同的变体（如将连字符替换为空格）
    if not image_path:
        variant_name = clean_image_name.replace('-', ' ')
        print(f"未找到图片 {clean_image_name}，尝试变体 {variant_name}")
        image_path = find_image(variant_name, source_file, source_dir)
    
    # 如果还没找到，尝试将空格替换为连字符
    if not image_path:
        variant_name = clean_image_name.replace(' ', '-')
        print(f"仍未找到，尝试变体 {variant_name}")
        image_path = find_image(variant_name, source_file, source_dir)
    
    if not image_path:
        print(f"警告: 找不到图片 {clean_image_name}，或其变体（{clean_image_name.replace('-', ' ')} 或 {clean_image_name.replace(' ', '-')})")
        return original
        
    print(f"找到图片: {image_path}")
        
    # 使用传入的目标目录
    new_name = copy_image(image_path, target_dir)
    
    if not new_name:
        print(f"警告: 无法复制图片 {clean_image_name}")
        return original
        
    print(f"成功复制图片为: {new_name}")
        
    # 返回标准Markdown格式的图片链接，直接引用图片文件（在文章目录中）
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
    
    # 首先处理可能的绝对路径引用（如 /images/...），将其规范化
    # 匹配 /images/ 开头的图片路径，将其转为相对路径
    absolute_image_pattern = r'\!\[([^\]]*)\]\(/images/([^)]+)\)'
    def replace_absolute_path(match):
        alt_text = match.group(1)
        image_name = match.group(2)
        return f"![{alt_text}]({image_name})"
    
    content = re.sub(absolute_image_pattern, replace_absolute_path, content)
    
    # 提取所有图片链接
    image_matches = []
    
    # 匹配Obsidian格式 ![[image.png]]
    obsidian_pattern = r'!\[\[(.*?)\]\]'
    for match in re.finditer(obsidian_pattern, content):
        image_name = match.group(1)
        alt_text = image_name.split('/')[-1]  # 使用文件名作为alt文本
        image_matches.append((match.group(0), image_name, alt_text, source_file, target_dir, source_dir))
    
    # 匹配Markdown格式 ![alt](image.png)，包括相对路径和绝对路径
    md_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    for match in re.finditer(md_pattern, content):
        alt_text = match.group(1) or ''
        image_name = match.group(2)
        # 只处理不是完整URL的图片路径
        if not (image_name.startswith('http://') or image_name.startswith('https://')):
            image_matches.append((match.group(0), image_name, alt_text, source_file, target_dir, source_dir))
    
    # 并行处理所有图片
    if image_matches:
        print(f"找到 {len(image_matches)} 个图片引用需要处理")
        processed_results = parallel_process(image_matches, process_single_image_with_target_dir, max_workers=4)
        
        # 替换原内容中的图片链接
        for i, (original, image_name, alt_text, _, _, _) in enumerate(image_matches):
            content = content.replace(original, processed_results[i], 1)
    
    return content