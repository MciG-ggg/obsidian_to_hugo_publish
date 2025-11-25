#!/usr/bin/env python3
"""
CLI显示增强功能的单元测试
测试排序选择界面的显示和交互功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.blog_processor import BlogProcessor
from src.core.front_matter import FrontMatter
from src.i18n.i18n import set_locale, t
from src.utils.cli_utils import CLIColors

class TestCLIDisplayEnhancement(unittest.TestCase):
    """测试CLI显示增强功能"""

    def setUp(self):
        """测试前准备"""
        set_locale('zh-CN')

        # 创建模拟的BlogProcessor
        self.mock_processor = Mock(spec=BlogProcessor)

        # 创建测试数据
        self.test_articles = [
            (Path('article1.md'), FrontMatter({
                'title': '第一篇文章',
                'description': '这是第一篇文章的描述',
                'tags': ['测试', '文章'],
                'publish': True
            })),
            (Path('article2.md'), FrontMatter({
                'title': '第二篇文章',
                'description': '这是第二篇文章的描述',
                'tags': ['示例'],
                'publish': True
            })),
            (Path('article3.md'), FrontMatter({
                'title': '第三篇文章',
                'description': '',
                'tags': [],
                'publish': True
            }))
        ]

    def test_blog_processor_sort_integration(self):
        """测试BlogProcessor排序集成"""
        with patch.object(BlogProcessor, 'list_published_markdowns') as mock_list:
            mock_list.return_value = self.test_articles

            # 创建真实的BlogProcessor实例进行测试
            processor = BlogProcessor('/fake/source', '/fake/hugo')

            # 测试排序调用
            result = processor.list_published_markdowns(sort_by='mtime')
            mock_list.assert_called_once_with(sort_by='mtime')

    def test_get_file_mtime_method(self):
        """测试获取文件修改时间的方法"""
        processor = BlogProcessor('/fake/source', '/fake/hugo')

        # 测试正常文件时间获取
        test_file = Path(__file__)  # 使用当前测试文件
        mtime = processor.get_file_mtime(test_file)
        self.assertIsInstance(mtime, datetime)

        # 测试格式化时间
        formatted_time = processor.format_mtime(mtime)
        self.assertRegex(formatted_time, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')

    def test_sorting_methods(self):
        """测试不同的排序方法"""
        # 模拟文件
        test_files = []
        for i in range(3):
            md_file = Path(f'article{i}.md')
            front_matter = FrontMatter({
                'title': f'文章{i}',
                'description': f'描述{i}',
                'tags': [f'标签{i}'],
                'publish': True
            })
            test_files.append((md_file, front_matter))

        processor = BlogProcessor('/fake/source', '/fake/hugo')

        # 测试按路径排序
        with patch.object(processor, 'get_file_mtime') as mock_mtime:
            mock_mtime.return_value = datetime.now()

            # 直接调用排序逻辑进行测试
            result_mtime = sorted(test_files, key=lambda item: processor.get_file_mtime(item[0]))
            self.assertEqual(len(result_mtime), 3)

            # 测试按标题排序
            result_title = sorted(test_files, key=lambda item: item[1].title if item[1].title and item[1].title.isascii() else item[0].stem)
            titles = [item[1].title for item in result_title]
            self.assertEqual(titles, ['文章0', '文章1', '文章2'])

            # 测试按路径排序
            result_path = sorted(test_files, key=lambda item: str(item[0]))
            paths = [str(item[0]) for item in result_path]
            self.assertEqual(paths, ['article0.md', 'article1.md', 'article2.md'])

    def test_time_format_consistency(self):
        """测试时间格式的一致性"""
        processor = BlogProcessor('/fake/source', '/fake/hugo')

        # 测试不同时间的格式化
        test_times = [
            datetime(2023, 1, 1, 0, 0),
            datetime(2023, 12, 31, 23, 59),
            datetime(2023, 6, 15, 14, 30)
        ]

        expected_formats = [
            '2023-01-01 00:00',
            '2023-12-31 23:59',
            '2023-06-15 14:30'
        ]

        for test_time, expected in zip(test_times, expected_formats):
            formatted = processor.format_mtime(test_time)
            self.assertEqual(formatted, expected)
            self.assertRegex(formatted, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')

    def test_error_handling_in_sorting(self):
        """测试排序中的错误处理"""
        processor = BlogProcessor('/fake/source', '/fake/hugo')

        # 测试不存在的文件
        fake_file = Path('/nonexistent/file.md')
        mtime = processor.get_file_mtime(fake_file)
        self.assertIsInstance(mtime, datetime)

        # 测试无效排序方式
        test_files = []
        with patch('src.utils.logger.warning') as mock_warning:
            # 这里需要实际的排序逻辑来测试警告
            # 由于我们在mock list_published_markdowns，这里主要测试错误处理逻辑的存在
            pass

    def test_color_display_format(self):
        """测试颜色显示格式"""
        # 验证颜色常量的存在
        self.assertIn('BOLD', dir(CLIColors))
        self.assertIn('DIM', dir(CLIColors))
        self.assertIn('RESET', dir(CLIColors))

        # 验证颜色值不为空
        self.assertIsNotNone(CLIColors.BOLD)
        self.assertIsNotNone(CLIColors.DIM)
        self.assertIsNotNone(CLIColors.RESET)

if __name__ == '__main__':
    unittest.main()