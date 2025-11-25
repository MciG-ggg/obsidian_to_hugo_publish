#!/usr/bin/env python3
"""
--select 参数排序优化功能的集成测试
测试完整的端到端工作流程
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os
import tempfile
import yaml
from datetime import datetime, timedelta

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from hugo_publish_blog import select_articles_to_publish, select_articles_to_unpublish, format_article_time_display
from src.core.config_manager import Config
from src.core.blog_processor import BlogProcessor
from src.core.front_matter import FrontMatter
from src.i18n.i18n import set_locale, t

class TestSelectSortingIntegration(unittest.TestCase):
    """测试--select参数排序优化功能的集成"""

    def setUp(self):
        """测试前准备"""
        set_locale('zh-CN')
        self.temp_dir = Path(tempfile.mkdtemp())

        # 创建测试目录结构
        self.source_dir = self.temp_dir / 'source'
        self.source_dir.mkdir()
        self.hugo_dir = self.temp_dir / 'hugo'
        self.hugo_dir.mkdir()

        # 创建测试配置文件
        self.config_file = self.temp_dir / 'config.yaml'
        config_data = {
            'paths': {
                'obsidian': {'vault': str(self.source_dir)},
                'hugo': {'blog': str(self.hugo_dir)}
            },
            'display': {
                'sort_by_mtime': True
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_articles(self, count=5):
        """创建测试文章文件"""
        articles = []
        base_time = datetime.now() - timedelta(days=10)

        for i in range(count):
            # 创建不同时间的文件
            file_time = base_time + timedelta(hours=i*12)  # 每篇文章间隔12小时
            article_file = self.source_dir / f'article_{i:02d}.md'

            # 创建不同内容的文章
            content = f"""---
publish: true
title: 测试文章 {i:02d}
description: 这是第{i}篇测试文章的描述
tags: [测试, 文章{i:02d}]
date: {file_time.strftime('%Y-%m-%d')}
---

# 测试文章 {i:02d}

这是第{i}篇文章的内容。
"""
            article_file.write_text(content, encoding='utf-8')

            # 设置文件修改时间
            import os
            os.utime(article_file, (file_time.timestamp(), file_time.timestamp()))

            articles.append(article_file)

        return articles

    def test_complete_select_publish_workflow(self):
        """测试完整的--select发布工作流程"""
        # 创建测试文章
        articles = self.create_test_articles(5)

        # 创建配置和处理器
        config = Config(str(self.config_file))
        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        # 测试选择界面
        with patch('builtins.input') as mock_input, \
             patch('builtins.print') as mock_print:

            # 模拟用户选择第0篇文章
            mock_input.return_value = '0'

            selected_files = select_articles_to_publish(processor, config)

            # 验证选择结果
            self.assertEqual(len(selected_files), 1)
            self.assertIn('article_00.md', selected_files[0])

            # 验证打印输出包含时间信息
            print_calls = [str(call) for call in mock_print.call_args_list]
            time_display_found = any('修改时间:' in call for call in print_calls)
            self.assertTrue(time_display_found, "显示应该包含修改时间信息")

    def test_sorting_configuration_impact(self):
        """测试排序配置对显示的影响"""
        articles = self.create_test_articles(3)

        # 创建禁用排序的配置
        config_data_disabled = {
            'paths': {
                'obsidian': {'vault': str(self.source_dir)},
                'hugo': {'blog': str(self.hugo_dir)}
            },
            'display': {
                'sort_by_mtime': False
            }
        }
        config_file_disabled = self.temp_dir / 'config_disabled.yaml'
        with open(config_file_disabled, 'w', encoding='utf-8') as f:
            yaml.dump(config_data_disabled, f)

        config_enabled = Config(str(self.config_file))
        config_disabled = Config(str(config_file_disabled))
        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        with patch('builtins.input') as mock_input, \
             patch('builtins.print') as mock_print:

            mock_input.return_value = ''  # 取消选择

            # 测试启用排序
            select_articles_to_publish(processor, config_enabled)
            print_calls_enabled = len(mock_print.call_args_list)

            mock_input.reset_mock()
            mock_print.reset_mock()

            # 测试禁用排序
            select_articles_to_publish(processor, config_disabled)
            print_calls_disabled = len(mock_print.call_args_list)

            # 两种配置都应该正常工作
            self.assertGreater(print_calls_enabled, 0)
            self.assertGreater(print_calls_disabled, 0)

    def test_time_display_format_consistency(self):
        """测试时间显示格式的一致性"""
        article_file = self.source_dir / 'test_time.md'
        article_file.write_text('---\npublish: true\ntitle: Test\n---\n# Test')

        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        # 测试时间显示格式
        time_display = format_article_time_display(processor, article_file)

        # 验证格式
        self.assertIn('修改时间:', time_display)
        self.assertRegex(time_display, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')

    def test_unpublish_workflow_consistency(self):
        """测试取消发布工作流程的一致性"""
        articles = self.create_test_articles(3)

        config = Config(str(self.config_file))
        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        with patch('builtins.input') as mock_input, \
             patch('builtins.print') as mock_print:

            mock_input.return_value = ''  # 取消选择

            # 测试发布选择界面
            select_articles_to_publish(processor, config)
            publish_calls = [str(call) for call in mock_print.call_args_list]

            mock_input.reset_mock()
            mock_print.reset_mock()

            # 测试取消发布选择界面
            select_articles_to_unpublish(processor, config)
            unpublish_calls = [str(call) for call in mock_print.call_args_list]

            # 验证两个界面的时间显示一致性
            publish_time_found = any('修改时间:' in call for call in publish_calls)
            unpublish_time_found = any('修改时间:' in call for call in unpublish_calls)

            self.assertTrue(publish_time_found, "发布界面应该显示时间信息")
            self.assertTrue(unpublish_time_found, "取消发布界面应该显示时间信息")

    def test_multiple_articles_selection(self):
        """测试多篇文章的选择"""
        articles = self.create_test_articles(5)

        config = Config(str(self.config_file))
        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        with patch('builtins.input') as mock_input, \
             patch('builtins.print') as mock_print:

            # 模拟用户选择多篇文章
            mock_input.return_value = '0,2,4'

            selected_files = select_articles_to_publish(processor, config)

            # 验证选择结果
            self.assertEqual(len(selected_files), 3)
            selected_names = [Path(f).name for f in selected_files]
            self.assertIn('article_00.md', selected_names)
            self.assertIn('article_02.md', selected_names)
            self.assertIn('article_04.md', selected_names)

    def test_all_selection_feature(self):
        """测试全选功能"""
        articles = self.create_test_articles(3)

        config = Config(str(self.config_file))
        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        with patch('builtins.input') as mock_input:
            # 模拟用户选择所有文章
            mock_input.return_value = 'all'

            selected_files = select_articles_to_publish(processor, config)

            # 验证选择了所有文章
            self.assertEqual(len(selected_files), 3)

    def test_sorting_order_verification(self):
        """测试排序顺序的验证"""
        articles = self.create_test_articles(5)

        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        # 获取排序后的文章列表
        published_articles = processor.list_published_markdowns(sort_by='mtime')

        # 验证排序顺序（应该从旧到新）
        if len(published_articles) >= 2:
            mtime_0 = processor.get_file_mtime(published_articles[0][0])
            mtime_1 = processor.get_file_mtime(published_articles[1][0])
            self.assertLessEqual(mtime_0, mtime_1, "文章应该按修改时间从旧到新排序")

    def test_internationalization_switching(self):
        """测试国际化切换功能"""
        articles = self.create_test_articles(1)

        # 测试中文界面
        set_locale('zh-CN')
        article_file = articles[0]
        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

        zh_time_display = format_article_time_display(processor, article_file)
        self.assertIn('修改时间:', zh_time_display)

        # 测试英文界面
        set_locale('en')
        en_time_display = format_article_time_display(processor, article_file)
        self.assertIn('Modified:', en_time_display)

    def test_error_handling_in_integration(self):
        """测试集成中的错误处理"""
        # 创建一个正常的文章文件
        normal_file = self.source_dir / 'normal.md'
        normal_file.write_text('---\npublish: true\ntitle: Normal\n---\n# Normal')

        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))
        config = Config(str(self.config_file))

        # 测试损坏的YAML文件不会影响其他文件的处理
        corrupted_file = self.source_dir / 'corrupted.md'
        corrupted_file.write_text('---\npublish: true\ninvalid: yaml: [\n---\n# Corrupted')

        with patch('builtins.input') as mock_input, \
             patch('builtins.print') as mock_print:

            mock_input.return_value = ''  # 取消选择

            # 应该能够正常处理，不因损坏文件而崩溃
            try:
                select_articles_to_publish(processor, config)
                # 如果没有异常，说明错误处理正常工作
            except Exception as e:
                self.fail(f"集成测试不应该因单个文件错误而崩溃: {e}")

    def test_performance_with_many_articles(self):
        """测试大量文章的性能"""
        # 创建较多文章测试性能
        articles = self.create_test_articles(20)

        processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))
        config = Config(str(self.config_file))

        import time
        start_time = time.time()

        with patch('builtins.input') as mock_input:
            mock_input.return_value = ''  # 取消选择

            # 测试文章列表生成性能
            published_articles = processor.list_published_markdowns(sort_by='mtime')

        end_time = time.time()
        processing_time = end_time - start_time

        # 验证性能指标（应该在合理范围内）
        self.assertLess(processing_time, 2.0, "20篇文章的排序处理应该在2秒内完成")
        self.assertEqual(len(published_articles), 20)

    def test_configuration_integration(self):
        """测试配置系统集成"""
        # 测试配置文件的各种状态
        config_scenarios = [
            # 正常配置
            {'display': {'sort_by_mtime': True}},
            # 缺少display配置
            {'paths': {'obsidian': {'vault': str(self.source_dir)}}},
            # 禁用排序
            {'display': {'sort_by_mtime': False}},
            # 空配置
            {}
        ]

        for i, config_data in enumerate(config_scenarios):
            config_file = self.temp_dir / f'config_{i}.yaml'
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f)

            config = Config(str(config_file))
            processor = BlogProcessor(str(self.source_dir), str(self.hugo_dir))

            with patch('builtins.input') as mock_input:
                mock_input.return_value = ''

                try:
                    select_articles_to_publish(processor, config)
                    # 配置应该能正常工作
                except Exception as e:
                    self.fail(f"配置场景 {i} 应该正常工作: {e}")

if __name__ == '__main__':
    unittest.main()