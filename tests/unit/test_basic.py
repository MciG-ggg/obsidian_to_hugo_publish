"""
单元测试文件
测试项目的各个模块和功能
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import Config
from src.core.blog_processor import BlogProcessor
from src.core.front_matter import FrontMatter, extract_yaml_and_content
from src.utils.utils import print_step, print_success, print_error, print_warning, print_info, print_header


class TestConfig:
    """测试配置管理模块"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        
        # 验证默认配置结构
        assert 'paths' in config.config
        assert 'repositories' in config.config
        assert 'images' in config.config
        assert 'posts' in config.config
        assert 'hugo' in config.config
        assert 'deployment' in config.config
        
        # 验证特定配置项
        assert config.get('paths.obsidian.vault') == '~/Documents/Obsidian Vault/'
        assert config.get('repositories.source.url') == 'git@github.com:MciG-ggg/hugo_blog.git'
        
    def test_config_get(self):
        """测试配置获取功能"""
        config = Config()
        
        # 正常获取
        assert config.get('paths.obsidian.vault') is not None
        
        # 获取不存在的键
        assert config.get('nonexistent.key') is None
        
        # 获取不存在的键但有默认值
        assert config.get('nonexistent.key', 'default_value') == 'default_value'


class TestFrontMatter:
    """测试前端数据模块"""
    
    def test_front_matter_creation(self):
        """测试FrontMatter对象创建"""
        data = {
            'title': 'Test Title',
            'date': '2023-01-01',
            'tags': ['test', 'example']
        }
        
        fm = FrontMatter(data)
        assert fm.title == 'Test Title'
        assert fm.date == '2023-01-01'
        assert fm.tags == ['test', 'example']
        
    def test_front_matter_update(self):
        """测试FrontMatter更新功能"""
        data = {
            'title': 'Test Title',
            'date': '2023-01-01'
        }
        
        fm = FrontMatter(data)
        fm.update({'tags': ['new', 'tags']})
        
        assert fm.tags == ['new', 'tags']
        assert fm.to_dict()['tags'] == ['new', 'tags']


class TestBlogProcessor:
    """测试博客处理器模块"""
    
    def test_mermaid_block_processing(self):
        """测试Mermaid代码块处理"""
        processor = BlogProcessor("/tmp/source", "/tmp/hugo")
        
        content_with_mermaid = "```mermaid\ngraph TD;\n    A-->B;\n    A-->C;\n    B-->D;\n    C-->D;\n    ```"
        
        processed = processor.process_mermaid_blocks(content_with_mermaid)
        
        # 验证转换后的格式
        assert "{{< mermaid >}}" in processed
        assert "{{< /mermaid >}}" in processed
        assert "graph TD;" in processed
        
    def test_note_block_processing(self):
        """测试Note块处理"""
        processor = BlogProcessor("/tmp/source", "/tmp/hugo")
        
        content_with_note = """> [!NOTE] Title
> This is a note block
> with multiple lines"""
        
        processed = processor.process_note_blocks(content_with_note)
        
        # 验证转换后的格式
        assert "{{< admonition type=\"note\" title=\"Title\" >}}" in processed
        assert "{{< /admonition >}}" in processed
        assert "This is a note block" in processed
        
    def test_note_block_processing_without_title(self):
        """测试没有标题的Note块处理"""
        processor = BlogProcessor("/tmp/source", "/tmp/hugo")
        
        content_with_note = """> [!NOTE]
> This is a note block
> with multiple lines"""
        
        processed = processor.process_note_blocks(content_with_note)
        
        # 验证转换后的格式，标题应为默认值"Note"
        assert "{{< admonition type=\"note\" title=\"Note\" >}}" in processed
        assert "{{< /admonition >}}" in processed
        assert "This is a note block" in processed


class TestUtils:
    """测试工具函数模块"""
    
    def test_print_functions(self, capsys):
        """测试打印函数"""
        # 这些函数仅测试不抛出异常
        print_step(1, "Test step")
        captured = capsys.readouterr()
        # 在测试环境中，国际化可能不可用，所以我们接受两种情况
        assert ("[步骤 1]" in captured.out or "step_prefix" in captured.out)
        
        print_success("Test success")
        captured = capsys.readouterr()
        # 在测试环境中，国际化可能不可用，所以我们接受两种情况
        assert ("✓" in captured.out or "success_prefix" in captured.out)
        
        print_error("Test error")
        captured = capsys.readouterr()
        # 在测试环境中，国际化可能不可用，所以我们接受两种情况
        assert ("✗" in captured.out or "error_prefix" in captured.out)
        
        print_warning("Test warning")
        captured = capsys.readouterr()
        # 在测试环境中，国际化可能不可用，所以我们接受两种情况
        assert ("!" in captured.out or "warning_prefix" in captured.out)
        
        print_info("Test info")
        captured = capsys.readouterr()
        # 在测试环境中，国际化可能不可用，所以我们接受两种情况
        assert ("ℹ" in captured.out or "info_prefix" in captured.out)
        
        print_header("Test header")
        captured = capsys.readouterr()
        assert "Test header" in captured.out