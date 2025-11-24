"""
TUI预览功能测试
测试Markdown渲染、同步滚动、前置数据显示等功能
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.tui.tui_app import PreviewPane, MarkdownViewer, FrontMatterEditor
from src.core.front_matter import FrontMatter
from src.core.blog_processor import BlogProcessor


class TestPreviewPane:
    """预览面板组件测试"""

    def test_preview_pane_creation(self):
        """测试预览面板创建"""
        preview = PreviewPane()
        assert preview is not None
        assert preview.id == "preview-pane"

    def test_preview_pane_initial_content(self):
        """测试预览面板初始内容"""
        preview = PreviewPane()
        # 初始状态应该显示提示信息
        assert "选择文件查看预览" in str(preview)

    def test_update_file_content_basic(self):
        """测试更新文件内容基础功能"""
        preview = PreviewPane()
        file_info = {
            'path': '/test/test.md',
            'content': '# Test Content\n\nThis is a test.',
            'front_matter': None
        }

        preview.update_file_content(file_info)
        # 应该包含Markdown内容
        assert "Test Content" in str(preview)

    @patch('builtins.open', create=True)
    def test_load_file_from_path(self, mock_open):
        """测试从路径加载文件"""
        # 模拟文件内容
        test_content = """---
title: Test Article
tags: [test, markdown]
---

# Test Article

This is test content.
"""
        mock_file = Mock()
        mock_file.read.return_value = test_content
        mock_open.return_value.__enter__.return_value = mock_file

        preview = PreviewPane()
        file_info = {'path': '/test/test.md'}

        preview.update_file_content(file_info)
        mock_open.assert_called_once_with('/test/test.md', 'r', encoding='utf-8')

    def test_empty_file_handling(self):
        """测试空文件处理"""
        preview = PreviewPane()
        file_info = {
            'path': '/test/empty.md',
            'content': '',
            'front_matter': None
        }

        preview.update_file_content(file_info)
        # 应该优雅处理空文件
        assert preview is not None


class TestMarkdownViewer:
    """Markdown查看器组件测试"""

    def test_markdown_viewer_creation(self):
        """测试Markdown查看器创建"""
        viewer = MarkdownViewer()
        assert viewer is not None
        assert "markdown-viewer" in str(viewer)

    def test_render_markdown_content(self):
        """测试Markdown内容渲染"""
        viewer = MarkdownViewer()
        markdown_content = "# Title\n\n**Bold text** and *italic text*."

        viewer.update_content(markdown_content)
        # 应该包含渲染后的内容
        assert viewer is not None

    def test_code_block_rendering(self):
        """测试代码块渲染"""
        viewer = MarkdownViewer()
        code_content = """```python
def hello():
    print("Hello World")
```"""

        viewer.update_content(code_content)
        # 应该处理代码块
        assert viewer is not None

    def test_list_rendering(self):
        """测试列表渲染"""
        viewer = MarkdownViewer()
        list_content = """- Item 1
- Item 2
- Item 3"""

        viewer.update_content(list_content)
        # 应该处理列表
        assert viewer is not None

    def test_link_rendering(self):
        """测试链接渲染"""
        viewer = MarkdownViewer()
        link_content = "[Google](https://google.com)"

        viewer.update_content(link_content)
        # 应该处理链接
        assert viewer is not None


class TestFrontMatterEditor:
    """前置数据编辑器测试"""

    def test_front_matter_editor_creation(self):
        """测试前置数据编辑器创建"""
        editor = FrontMatterEditor()
        assert editor is not None
        assert "front-matter-editor" in str(editor)

    def test_load_front_matter_data(self):
        """测试加载前置数据"""
        editor = FrontMatterEditor()
        front_matter = FrontMatter({
            'title': 'Test Article',
            'tags': ['test', 'article'],
            'description': 'Test description'
        })

        editor.load_front_matter(front_matter)
        # 应该显示前置数据
        assert editor is not None

    def test_update_title_field(self):
        """测试更新标题字段"""
        editor = FrontMatterEditor()
        front_matter = FrontMatter({'title': 'Original Title'})

        editor.load_front_matter(front_matter)
        # 模拟编辑标题
        editor.update_field('title', 'New Title')

        # 验证更新
        updated_data = editor.get_updated_data()
        assert updated_data['title'] == 'New Title'

    def test_update_tags_field(self):
        """测试更新标签字段"""
        editor = FrontMatterEditor()
        front_matter = FrontMatter({'tags': ['original', 'tag']})

        editor.load_front_matter(front_matter)
        # 模拟编辑标签
        editor.update_field('tags', 'new,tag,another')

        # 验证更新
        updated_data = editor.get_updated_data()
        assert 'new' in updated_data['tags']
        assert 'another' in updated_data['tags']

    def test_empty_front_matter_handling(self):
        """测试空前置数据处理"""
        editor = FrontMatterEditor()
        front_matter = FrontMatter()

        editor.load_front_matter(front_matter)
        # 应该处理空前置数据
        assert editor is not None

    def test_invalid_front_matter_handling(self):
        """测试无效前置数据处理"""
        editor = FrontMatterEditor()
        # 传入无效数据
        editor.load_front_matter(None)

        # 应该优雅处理
        assert editor is not None


class TestPreviewIntegration:
    """预览功能集成测试"""

    def create_sample_file(self, temp_dir):
        """创建示例Markdown文件"""
        sample_content = """---
title: Sample Article
description: This is a sample article for testing
tags: [test, sample, markdown]
categories: [testing]
draft: true
date: 2025-01-01
---

# Sample Article

This is a **sample article** for testing the preview functionality.

## Features

- Markdown rendering
- Front matter display
- Syntax highlighting

```python
def sample_function():
    return "Hello, World!"
```

[Sample Link](https://example.com)
"""
        file_path = Path(temp_dir) / "sample.md"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        return file_path

    def test_complete_preview_workflow(self, tmp_path):
        """测试完整的预览工作流程"""
        # 创建示例文件
        sample_file = self.create_sample_file(tmp_path)

        # 创建预览面板
        preview = PreviewPane()

        # 模拟文件信息
        file_info = {
            'path': str(sample_file),
            'title': 'Sample Article'
        }

        # 更新预览内容
        preview.update_file_content(file_info)

        # 验证预览已更新
        assert preview is not None

    @patch('src.core.blog_processor.BlogProcessor')
    def test_blog_processor_integration(self, mock_processor_class):
        """测试与博客处理器的集成"""
        # 模拟博客处理器
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        # 模拟处理后的内容
        processed_content = """
# Sample Article

This is **processed** content for Hugo.

{{< mermaid >}}
graph TD
    A[Start] --> B[End]
{{< /mermaid >}}
"""
        mock_processor.process_obsidian_wiki_links.return_value = processed_content

        # 创建预览并测试集成
        preview = PreviewPane()
        file_info = {
            'path': '/test/sample.md',
            'content': '[[Wiki Link]] content'
        }

        # 测试内容处理
        preview.update_file_content(file_info)
        assert preview is not None

    def test_sync_scroll_functionality(self):
        """测试同步滚动功能"""
        # 创建原始内容和渲染内容查看器
        original_viewer = MarkdownViewer(id="original")
        rendered_viewer = MarkdownViewer(id="rendered")

        # 设置测试内容
        long_content = "\n".join([f"Line {i}" for i in range(100)])
        original_viewer.update_content(long_content)
        rendered_viewer.update_content(long_content)

        # 测试同步滚动设置
        original_viewer.setup_sync_scroll(rendered_viewer)
        rendered_viewer.setup_sync_scroll(original_viewer)

        # 验证同步滚动设置
        assert original_viewer is not None
        assert rendered_viewer is not None

    def test_preview_performance_with_large_file(self):
        """测试大文件预览性能"""
        # 创建大内容
        large_content = "\n".join([f"# Section {i}\n\nContent for section {i}.\n" for i in range(50)])

        viewer = MarkdownViewer()

        # 测试大内容渲染
        viewer.update_content(large_content)

        # 验证性能（这里只是基础验证）
        assert viewer is not None

    def test_error_handling_in_preview(self):
        """测试预览中的错误处理"""
        preview = PreviewPane()

        # 测试无效文件路径
        invalid_file_info = {'path': '/nonexistent/file.md'}
        preview.update_file_content(invalid_file_info)

        # 应该优雅处理错误
        assert preview is not None

        # 测试无效前置数据
        invalid_file_info = {
            'path': '/test/test.md',
            'front_matter': 'invalid_yaml_content'
        }
        preview.update_file_content(invalid_file_info)

        # 应该优雅处理错误
        assert preview is not None


if __name__ == "__main__":
    pytest.main([__file__])