#!/usr/bin/env python3
# 图片处理工具
# 用于处理博客中的图片：压缩、调整大小等

from PIL import Image
import os
from pathlib import Path
import shutil
import re

def optimize_image(img_path, max_width=800, quality=85):
    """优化图片尺寸和质量"""
    try:
        with Image.open(img_path) as img:
            # 保持宽高比调整大小
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 转换为RGB模式（如果是RGBA）
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            
            # 保存优化后的图片
            img.save(img_path, 'JPEG', quality=quality, optimize=True)
            return True
    except Exception as e:
        print(f"处理图片 {img_path} 时出错: {str(e)}")
        return False

def process_article_images(article_dir, backup=True):
    """处理文章目录中的所有图片"""
    processed = []
    article_dir = Path(article_dir)
    
    # 创建备份目录
    if backup:
        backup_dir = article_dir / 'images_backup'
        backup_dir.mkdir(exist_ok=True)
    
    # 查找所有图片文件
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif')
    for img_path in article_dir.rglob('*'):
        if img_path.suffix.lower() in image_extensions:
            # 跳过备份目录中的文件
            if 'images_backup' in str(img_path):
                continue
                
            # 备份原始图片
            if backup:
                backup_path = backup_dir / img_path.name
                shutil.copy2(img_path, backup_path)
            
            # 优化图片
            if optimize_image(img_path):
                processed.append(img_path)
    
    return processed

def update_image_references(md_file, processed_images):
    """更新Markdown文件中的图片引用"""
    md_file = Path(md_file)
    if not md_file.exists() or not md_file.suffix == '.md':
        return False
    
    content = md_file.read_text(encoding='utf-8')
    modified = False
    
    # 更新图片引用
    for img_path in processed_images:
        img_name = img_path.name
        # 匹配Markdown图片语法
        pattern = rf'!\[([^\]]*)\]\([^)]*{re.escape(img_name)}\)'
        replacement = f'![\1]({img_path.relative_to(md_file.parent)})'
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            modified = True
    
    # 如果有修改，保存文件
    if modified:
        md_file.write_text(content, encoding='utf-8')
    
    return modified

if __name__ == '__main__':
    print("This module is intended to be imported, not run directly.")
