#!/usr/bin/env python3
"""
--select 参数排序优化功能的端到端测试
验证完整用户场景和功能验收标准
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import os
import tempfile
import yaml
import subprocess
from datetime import datetime, timedelta

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

class TestSelectSortingE2E(unittest.TestCase):
    """测试--select参数排序优化功能的端到端场景"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # 创建完整的测试目录结构
        self.source_dir = self.temp_dir / 'obsidian_vault'
        self.source_dir.mkdir()
        self.hugo_dir = self.temp_dir / 'hugo_blog'
        self.hugo_dir.mkdir()

        # 创建测试配置文件
        self.config_file = self.temp_dir / 'config.yaml'
        config_data = {
            'paths': {
                'obsidian': {
                    'vault': str(self.source_dir),
                    'images': str(self.source_dir / 'images')
                },
                'hugo': {
                    'blog': str(self.hugo_dir),
                    'public': 'public'
                }
            },
            'display': {
                'sort_by_mtime': True
            },
            'logging': {
                'level': 'INFO'
            }
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)

        # 切换到项目根目录
        os.chdir(project_root)

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_realistic_test_articles(self, count=8):
        """创建接近真实的测试文章"""
        articles = []
        base_time = datetime.now() - timedelta(days=30)

        titles = [
            "Python编程入门指南",
            "机器学习基础概念",
            "Hugo博客建站教程",
            "Obsidian使用技巧",
            "数据结构详解",
            "算法设计模式",
            "Web开发最佳实践",
            "Git版本控制精通"
        ]

        descriptions = [
            "详细介绍Python编程的基础知识和最佳实践",
            "深入浅出地讲解机器学习的基本概念和算法",
            "手把手教你使用Hugo搭建个人博客",
            "提高Obsidian使用效率的实用技巧汇总",
            "全面解析常见的数据结构和应用场景",
            "软件设计中常用的算法模式和解决方案",
            "现代Web开发的技术栈和最佳实践",
            "Git版本控制工具的完整学习指南"
        ]

        tags_list = [
            ["Python", "编程", "入门"],
            ["机器学习", "AI", "算法"],
            ["Hugo", "博客", "建站"],
            ["Obsidian", "笔记", "效率"],
            ["数据结构", "计算机科学", "基础"],
            ["算法", "设计模式", "软件工程"],
            ["Web", "开发", "前端", "后端"],
            ["Git", "版本控制", "协作"]
        ]

        for i in range(count):
            # 创建不同时间间隔的文件，模拟真实使用场景
            days_offset = i * 3  # 每3天一篇
            hours_offset = i * 2  # 每篇间隔2小时
            file_time = base_time + timedelta(days=days_offset, hours=hours_offset)

            # 创建带时间信息的文件名
            date_prefix = file_time.strftime('%Y%m%d')
            filename = f'{date_prefix}-{"-".join(titles[i].split()[:2])}.md'
            article_file = self.source_dir / filename

            # 创建真实的文章内容
            content = f"""---
publish: true
title: {titles[i]}
description: {descriptions[i]}
tags: {tags_list[i]}
date: {file_time.strftime('%Y-%m-%d')}
lastmod: {file_time.strftime('%Y-%m-%d')}
author: Test Author
categories: [技术]
---

# {titles[i]}

## 概述

{descriptions[i]}

## 主要内容

### 基础概念

这里介绍{titles[i]}的基础概念和核心思想。

### 实践案例

通过实际案例来理解{titles[i]}的应用。

### 常见问题

解答在学习{titles[i]}过程中可能遇到的常见问题。

## 总结

{titles[i]}是一个重要的话题，值得深入学习和实践。

---

**标签**: {', '.join(tags_list[i])}
**创建时间**: {file_time.strftime('%Y-%m-%d %H:%M')}
"""
            article_file.write_text(content, encoding='utf-8')

            # 设置文件修改时间，模拟真实场景
            import os
            os.utime(article_file, (file_time.timestamp(), file_time.timestamp()))

            articles.append({
                'file': article_file,
                'title': titles[i],
                'description': descriptions[i],
                'tags': tags_list[i],
                'mtime': file_time
            })

        return articles

    def test_realistic_user_scenario_chinese_interface(self):
        """测试真实用户场景 - 中文界面"""
        # 创建真实的测试文章
        articles = self.create_realistic_test_articles(6)

        # 使用主脚本测试 --select 参数
        script_path = project_root / 'hugo_publish_blog.py'

        with patch('builtins.input') as mock_input, \
             patch('sys.argv', ['hugo_publish_blog.py', 'publish', '--select', '--config', str(self.config_file)]):

            # 模拟用户交互
            inputs = ['']  # 用户选择取消
            mock_input.side_value = inputs

            try:
                # 导入并测试主模块
                import hugo_publish_blog as main_module

                # 创建配置对象
                config = main_module.Config(str(self.config_file))
                processor = main_module.BlogProcessor(
                    config.get('paths.obsidian.vault'),
                    config.get('paths.hugo.blog'),
                    config_file=str(self.config_file)
                )

                # 测试选择函数
                with patch('builtins.input', return_value=''):
                    selected_files = main_module.select_articles_to_publish(processor, config)

                # 验证结果
                self.assertIsInstance(selected_files, list)

            except SystemExit:
                # 正常退出（用户取消选择）
                pass
            except Exception as e:
                self.fail(f"真实用户场景测试失败: {e}")

    def test_sorting_order_visual_verification(self):
        """测试排序顺序的视觉验证"""
        articles = self.create_realistic_test_articles(5)

        # 导入必要模块
        import hugo_publish_blog as main_module

        config = main_module.Config(str(self.config_file))
        processor = main_module.BlogProcessor(
            config.get('paths.obsidian.vault'),
            config.get('paths.hugo.blog'),
            config_file=str(self.config_file)
        )

        # 获取排序后的文章列表
        published_articles = processor.list_published_markdowns(sort_by='mtime')

        # 验证排序顺序和完整性
        self.assertEqual(len(published_articles), 5, "应该找到5篇文章")

        # 验证时间顺序（从旧到新）
        previous_mtime = None
        for article_tuple in published_articles:
            article_file, front_matter = article_tuple
            current_mtime = processor.get_file_mtime(article_file)

            if previous_mtime is not None:
                self.assertLessEqual(
                    previous_mtime,
                    current_mtime,
                    f"文章 {front_matter.title} 应该在 {previous_mtime} 之后"
                )
            previous_mtime = current_mtime

        # 验证每篇文章都有有效的标题和描述
        for article_file, front_matter in published_articles:
            self.assertIsNotNone(front_matter.title)
            self.assertIsNotNone(front_matter.description)
            self.assertTrue(front_matter.publish)

    def test_multilingual_interface_switching(self):
        """测试多语言界面切换"""
        articles = self.create_realistic_test_articles(3)

        # 导入必要模块
        import hugo_publish_blog as main_module
        from src.i18n.i18n import set_locale, t

        # 测试中文界面
        set_locale('zh-CN')
        config = main_module.Config(str(self.config_file))
        processor = main_module.BlogProcessor(
            config.get('paths.obsidian.vault'),
            config.get('paths.hugo.blog'),
            config_file=str(self.config_file)
        )

        article_file = list(self.source_dir.glob('*.md'))[0]
        zh_time_display = main_module.format_article_time_display(processor, article_file)
        self.assertIn('修改时间:', zh_time_display)

        # 测试英文界面
        set_locale('en')
        en_time_display = main_module.format_article_time_display(processor, article_file)
        self.assertIn('Modified:', en_time_display)

        # 恢复中文界面
        set_locale('zh-CN')

    def test_error_recovery_robustness(self):
        """测试错误恢复的健壮性"""
        # 创建正常文章
        normal_articles = self.create_realistic_test_articles(3)

        # 创建有问题的文件
        corrupted_file = self.source_dir / 'corrupted-article.md'
        corrupted_file.write_text('---\npublish: true\ninvalid: yaml: content: [\n---\n# Corrupted')

        empty_file = self.source_dir / 'empty-article.md'
        empty_file.write_text('')

        import hugo_publish_blog as main_module

        config = main_module.Config(str(self.config_file))
        processor = main_module.BlogProcessor(
            config.get('paths.obsidian.vault'),
            config.get('paths.hugo.blog'),
            config_file=str(self.config_file)
        )

        # 测试系统在有问题的文件存在时仍能正常工作
        try:
            published_articles = processor.list_published_markdowns(sort_by='mtime')

            # 应该至少能处理正常的文章
            self.assertGreaterEqual(len(published_articles), 3)

            # 验证正常的文章被正确处理
            valid_articles = [
                (file, fm) for file, fm in published_articles
                if 'corrupted' not in str(file) and 'empty' not in str(file)
            ]
            self.assertGreaterEqual(len(valid_articles), 3)

        except Exception as e:
            self.fail(f"系统应该在有问题的文件存在时仍能正常工作: {e}")

    def test_performance_acceptance_criteria(self):
        """测试性能验收标准"""
        # 创建较多文章测试性能
        articles = self.create_realistic_test_articles(50)  # 50篇文章

        import hugo_publish_blog as main_module
        import time

        config = main_module.Config(str(self.config_file))
        processor = main_module.BlogProcessor(
            config.get('paths.obsidian.vault'),
            config.get('paths.hugo.blog'),
            config_file=str(self.config_file)
        )

        # 测试排序性能
        start_time = time.time()
        published_articles = processor.list_published_markdowns(sort_by='mtime')
        end_time = time.time()

        processing_time = end_time - start_time

        # 验证性能指标
        self.assertEqual(len(published_articles), 50, "应该处理所有50篇文章")
        self.assertLess(processing_time, 2.0, "50篇文章的排序应该在2秒内完成")

        # 测试内存使用（简单验证）
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()

        # 验证内存使用在合理范围内（小于100MB）
        self.assertLess(memory_info.rss, 100 * 1024 * 1024, "内存使用应该在合理范围内")

    def test_user_acceptance_criteria(self):
        """测试用户验收标准"""
        articles = self.create_realistic_test_articles(4)

        import hugo_publish_blog as main_module

        config = main_module.Config(str(self.config_file))
        processor = main_module.BlogProcessor(
            config.get('paths.obsidian.vault'),
            config.get('paths.hugo.blog'),
            config_file=str(self.config_file)
        )

        # 验证主要功能
        published_articles = processor.list_published_markdowns(sort_by='mtime')

        # 验收标准1: 支持3种排序方式
        sort_methods = ['mtime', 'title', 'path']
        for method in sort_methods:
            try:
                result = processor.list_published_markdowns(sort_by=method)
                self.assertIsInstance(result, list, f"排序方式 {method} 应该正常工作")
            except Exception as e:
                self.fail(f"排序方式 {method} 不应该出错: {e}")

        # 验收标准2: 显示时间信息，格式统一
        for article_file, front_matter in published_articles:
            time_display = main_module.format_article_time_display(processor, article_file)
            self.assertIn('修改时间:', time_display, "应该显示修改时间")
            self.assertRegex(time_display, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', "时间格式应该统一")

        # 验收标准3: 配置文件支持排序开关
        sort_enabled = config.get('display.sort_by_mtime', True)
        self.assertIsInstance(sort_enabled, bool, "排序配置应该是布尔值")

        # 验收标准4: 中英文界面完整支持
        from src.i18n.i18n import set_locale, t

        set_locale('zh-CN')
        zh_label = t("modified_time_label", mtime="2023-12-25 15:30")
        self.assertIn("修改时间:", zh_label)

        set_locale('en')
        en_label = t("modified_time_label", mtime="2023-12-25 15:30")
        self.assertIn("Modified:", en_label)

        # 恢复中文界面
        set_locale('zh-CN')

    def test_backwards_compatibility_verification(self):
        """测试向后兼容性验证"""
        articles = self.create_realistic_test_articles(2)

        import hugo_publish_blog as main_module

        config = main_module.Config(str(self.config_file))
        processor = main_module.BlogProcessor(
            config.get('paths.obsidian.vault'),
            config.get('paths.hugo.blog'),
            config_file=str(self.config_file)
        )

        # 测试不带参数的调用（向后兼容）
        result_default = processor.list_published_markdowns()

        # 测试带参数的调用（新功能）
        result_with_param = processor.list_published_markdowns(sort_by='mtime')

        # 两种调用方式都应该工作
        self.assertIsInstance(result_default, list, "不带参数的调用应该仍然有效")
        self.assertIsInstance(result_with_param, list, "带参数的调用应该有效")

        # 验证结果的一致性
        self.assertEqual(len(result_default), len(result_with_param))

    def test_end_to_end_workflow_simulation(self):
        """测试端到端工作流程模拟"""
        # 创建真实的测试环境
        articles = self.create_realistic_test_articles(5)

        import hugo_publish_blog as main_module

        # 模拟完整的用户工作流程
        config = main_module.Config(str(self.config_file))
        processor = main_module.BlogProcessor(
            config.get('paths.obsidian.vault'),
            config.get('paths.hugo.blog'),
            config_file=str(self.config_file)
        )

        # 1. 用户查看可用文章
        published_articles = processor.list_published_markdowns(sort_by='mtime')
        self.assertEqual(len(published_articles), 5)

        # 2. 用户选择要发布的文章
        with patch('builtins.input') as mock_input:
            mock_input.return_value = '0'  # 选择第一篇文章
            selected_files = main_module.select_articles_to_publish(processor, config)

        self.assertEqual(len(selected_files), 1)

        # 3. 验证选择的文件是最新编辑的文章（因为按时间排序，最新编辑的在最后）
        selected_file = Path(selected_files[0])

        # 在按时间排序的情况下，序号最大的应该是最新编辑的文章
        latest_file = published_articles[-1][0]  # 排序后的最后一篇是最新的
        self.assertEqual(selected_file.name, latest_file.name)

if __name__ == '__main__':
    unittest.main()