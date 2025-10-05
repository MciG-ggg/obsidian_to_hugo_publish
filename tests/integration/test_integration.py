"""
集成测试 - 测试模块之间的交互
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import Config
from src.core.blog_processor import BlogProcessor
from src.core.front_matter import FrontMatter
from src.i18n.i18n import set_locale


class TestConfigBlogProcessorIntegration:
    """测试配置管理器与博客处理器的集成"""
    
    def test_config_blog_processor_flow(self):
        """测试配置和博客处理器的集成流程"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            hugo_dir = Path(temp_dir) / "hugo"
            
            source_dir.mkdir(parents=True, exist_ok=True)
            hugo_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建测试配置
            config_data = {
                'paths': {
                    'obsidian': {
                        'vault': str(source_dir)
                    },
                    'hugo': {
                        'blog': str(hugo_dir)
                    }
                },
                'repositories': {
                    'source': {
                        'url': 'git@example.com:test/blog-source.git',
                        'branch': 'main'
                    },
                    'pages': {
                        'url': 'git@example.com:test/test.github.io.git',
                        'branch': 'main'
                    }
                }
            }
            
            # 模拟配置文件
            config_path = Path(temp_dir) / "config.yaml"
            import yaml
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f)
            
            # 使用配置创建博客处理器
            processor = BlogProcessor(source_dir, hugo_dir)
            assert processor.source_dir == source_dir
            assert processor.hugo_dir == hugo_dir


class TestFrontMatterI18nIntegration:
    """测试前端数据和国际化的集成"""
    
    def test_front_matter_with_i18n(self):
        """测试前端数据处理结合国际化"""
        # 测试在不同语言环境下处理前端数据
        set_locale('en')  # 设置为英文
        
        # 创建测试前端数据
        front_matter_data = {
            'title': 'Test Article',
            'date': '2023-01-01',
            'tags': ['test', 'integration'],
            'categories': ['Testing'],
            'description': 'This is a test article'
        }
        
        fm = FrontMatter(front_matter_data)
        assert fm.title == 'Test Article'
        assert fm.tags == ['test', 'integration']
        
        # 验证可以正常转换为字典
        fm_dict = fm.to_dict()
        assert 'title' in fm_dict
        assert 'tags' in fm_dict


class TestMarkdownProcessingIntegration:
    """测试Markdown处理的集成"""
    
    def test_complete_markdown_processing_flow(self):
        """测试完整的Markdown处理流程"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            hugo_dir = Path(temp_dir) / "hugo"
            
            source_dir.mkdir(parents=True, exist_ok=True)
            hugo_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建测试Markdown文件
            test_md = source_dir / "test_article.md"
            test_content = """---
title: Test Article
date: 2023-01-01
publish: true
tags: [test, integration]
categories: [Testing]
---
# Test Article

This is a test article content.

```mermaid
graph TD;
    A-->B;
    A-->C;
```

> [!NOTE]
> This is a note block.
"""
            with open(test_md, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # 创建博客处理器并处理文件
            processor = BlogProcessor(source_dir, hugo_dir)
            
            # 检查是否能找到并处理发布文件
            published = processor.list_published_markdowns()
            assert len(published) == 1
            assert published[0][0] == test_md
            
            # 处理文件
            processed_files = processor.process_markdown_files()
            assert len(processed_files) == 1
            
            # 检查生成的文章文件
            expected_article_dir = hugo_dir / "content" / "post" / "test-article"
            assert expected_article_dir.exists()
            expected_article_file = expected_article_dir / "index.md"
            assert expected_article_file.exists()
            
            # 检查文章内容
            with open(expected_article_file, 'r', encoding='utf-8') as f:
                article_content = f.read()
                
            # 验证Mermaid块被正确转换
            assert "{{< mermaid >}}" in article_content
            assert "{{< /mermaid >}}" in article_content
            
            # 验证Note块被正确转换
            assert "{{< admonition type=\"note\" title=\"Note\" >}}" in article_content
            assert "{{< /admonition >}}" in article_content