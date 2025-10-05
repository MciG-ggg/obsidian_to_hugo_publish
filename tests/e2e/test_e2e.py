"""
端到端测试 - 测试完整的使用流程
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os
import subprocess
from unittest.mock import patch, MagicMock


class TestEndToEnd:
    """端到端测试"""
    
    def test_complete_publishing_workflow(self):
        """测试完整的发布工作流程"""
        # 这个测试会比较复杂，需要模拟完整的发布流程
        # 由于涉及实际的Git操作和文件系统操作，我们将进行部分模拟测试
        
        # 添加项目根目录到Python路径
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        from src.core.config_manager import Config
        from src.core.blog_processor import BlogProcessor
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            hugo_dir = Path(temp_dir) / "hugo"
            
            source_dir.mkdir(parents=True, exist_ok=True)
            hugo_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建测试Markdown文件
            test_md = source_dir / "test_article.md"
            test_content = """---
title: Test End-to-End Article
date: 2023-01-01
publish: true
tags: [e2e, test]
categories: [Testing]
description: This is an end-to-end test article
---
# Test End-to-End Article

This is a test article to verify the complete workflow.

```mermaid
graph TD;
    A-->B;
    A-->C;
```

> [!NOTE]
> This is a note block for end-to-end testing.
"""
            with open(test_md, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # 使用配置和处理器
            processor = BlogProcessor(source_dir, hugo_dir)
            
            # 验证文章被正确识别为可发布
            published_articles = processor.list_published_markdowns()
            assert len(published_articles) == 1
            
            # 处理文章
            processed_files = processor.process_markdown_files()
            assert len(processed_files) == 1
            
            # 验证生成的文章
            expected_article_dir = hugo_dir / "content" / "post" / "test-end-to-end-article"
            assert expected_article_dir.exists()
            expected_article_file = expected_article_dir / "index.md"
            assert expected_article_file.exists()
            
            # 检查生成的文章内容
            with open(expected_article_file, 'r', encoding='utf-8') as f:
                article_content = f.read()
                
            # 验证文章标题和描述被正确处理
            assert "Test End-to-End Article" in article_content
            assert "This is an end-to-end test article" in article_content
            
            # 验证Mermaid和Note块被正确转换
            assert "{{< mermaid >}}" in article_content
            assert "{{< /admonition >}}" in article_content


    def test_error_handling_workflow(self):
        """测试错误处理工作流程"""
        # 添加项目根目录到Python路径
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        from src.core.blog_processor import BlogProcessor
        
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            hugo_dir = Path(temp_dir) / "hugo"
            
            source_dir.mkdir(parents=True, exist_ok=True)
            hugo_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建一个有问题的Markdown文件（没有publish字段）
            test_md = source_dir / "test_no_publish.md"
            test_content = """---
title: Test No Publish
date: 2023-01-01
tags: [test]
---
# Test No Publish

This article has no publish field.
"""
            with open(test_md, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # 创建一个publish为false的文件
            test_md2 = source_dir / "test_unpublished.md"
            test_content2 = """---
title: Test Unpublished
date: 2023-01-01
publish: false
tags: [test]
---
# Test Unpublished

This article is unpublished.
"""
            with open(test_md2, 'w', encoding='utf-8') as f:
                f.write(test_content2)
            
            # 创建一个正常的可发布文件
            test_md3 = source_dir / "test_published.md"
            test_content3 = """---
title: Test Published
date: 2023-01-01
publish: true
tags: [test]
---
# Test Published

This article is published.
"""
            with open(test_md3, 'w', encoding='utf-8') as f:
                f.write(test_content3)
            
            processor = BlogProcessor(source_dir, hugo_dir)
            
            # 只有publish: true的文章被处理
            published_articles = processor.list_published_markdowns()
            assert len(published_articles) == 1
            assert published_articles[0][1].title == "Test Published"
            
            # 验证处理流程只处理publish: true的文章
            processed_files = processor.process_markdown_files()
            assert len(processed_files) == 1


    def test_config_validation_e2e(self):
        """测试配置验证的端到端流程"""
        # 添加项目根目录到Python路径
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        from src.core.config_manager import Config
        
        # 测试默认配置
        config = Config()
        # 验证配置是否能正确加载
        assert config.get('paths.obsidian.vault') is not None
        assert config.get('repositories.source.url') is not None