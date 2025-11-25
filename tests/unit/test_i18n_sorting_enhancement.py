#!/usr/bin/env python3
"""
国际化增强功能的单元测试
测试排序功能的国际化支持
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.i18n.i18n import set_locale, t
from src.core.blog_processor import BlogProcessor
from src.core.front_matter import FrontMatter

class TestI18nSortingEnhancement(unittest.TestCase):
    """测试国际化增强功能"""

    def setUp(self):
        """测试前准备"""
        # 设置测试语言为中文
        set_locale('zh-CN')

    def test_modified_time_label_chinese(self):
        """测试中文时间标签"""
        # 测试时间标签翻译
        time_label = t("modified_time_label", mtime="2023-12-25 15:30")
        self.assertEqual(time_label, "修改时间: 2023-12-25 15:30")

    def test_modified_time_label_english(self):
        """测试英文时间标签"""
        # 切换到英文
        set_locale('en')

        time_label = t("modified_time_label", mtime="2023-12-25 15:30")
        self.assertEqual(time_label, "Modified: 2023-12-25 15:30")

    def test_sort_by_mtime_config_translation(self):
        """测试排序配置项的翻译"""
        # 中文测试
        set_locale('zh-CN')
        config_label = t("sort_by_mtime_config")
        self.assertEqual(config_label, "按修改时间排序")

        # 英文测试
        set_locale('en')
        config_label = t("sort_by_mtime_config")
        self.assertEqual(config_label, "Sort by modification time")

    def test_modified_time_unavailable_translation(self):
        """测试时间不可用时的翻译"""
        # 中文测试
        set_locale('zh-CN')
        unavailable_msg = t("modified_time_unavailable")
        self.assertEqual(unavailable_msg, "时间信息不可用")

        # 英文测试
        set_locale('en')
        unavailable_msg = t("modified_time_unavailable")
        self.assertEqual(unavailable_msg, "Time information unavailable")

    def test_time_format_translation(self):
        """测试时间格式说明的翻译"""
        # 中文测试
        set_locale('zh-CN')
        format_desc = t("modified_time_format")
        self.assertEqual(format_desc, "YYYY-MM-DD HH:MM")

        # 英文测试
        set_locale('en')
        format_desc = t("modified_time_format")
        self.assertEqual(format_desc, "YYYY-MM-DD HH:MM format description")

    def test_parameterized_time_translation(self):
        """测试参数化的时间翻译"""
        # 测试不同的时间参数
        test_times = [
            "2023-01-01 00:00",
            "2023-12-31 23:59",
            "2023-06-15 14:30"
        ]

        # 中文测试
        set_locale('zh-CN')
        for test_time in test_times:
            time_label = t("modified_time_label", mtime=test_time)
            self.assertEqual(time_label, f"修改时间: {test_time}")

        # 英文测试
        set_locale('en')
        for test_time in test_times:
            time_label = t("modified_time_label", mtime=test_time)
            self.assertEqual(time_label, f"Modified: {test_time}")

    def test_translation_key_fallback(self):
        """测试翻译键的后备机制"""
        # 测试不存在的翻译键
        non_existent_key = t("non_existent_time_key")
        self.assertEqual(non_existent_key, "non_existent_time_key")

    def test_language_switching(self):
        """测试语言切换功能"""
        # 先设置中文
        set_locale('zh-CN')
        chinese_label = t("modified_time_label", mtime="2023-01-01 12:00")

        # 切换到英文
        set_locale('en')
        english_label = t("modified_time_label", mtime="2023-01-01 12:00")

        # 验证切换后的翻译不同
        self.assertNotEqual(chinese_label, english_label)
        self.assertEqual(chinese_label, "修改时间: 2023-01-01 12:00")
        self.assertEqual(english_label, "Modified: 2023-01-01 12:00")

    def test_existing_translations_compatibility(self):
        """测试与现有翻译的兼容性"""
        # 确保现有的翻译键仍然有效
        set_locale('zh-CN')

        # 测试一些现有的翻译键
        existing_keys = [
            "file_label",
            "description_label",
            "tags_label",
            "no_published_articles",
            "selected_count"
        ]

        for key in existing_keys:
            translation = t(key)
            self.assertIsNotNone(translation)
            self.assertNotEqual(translation, key)  # 应该有实际的翻译内容

    def test_translation_with_multiple_parameters(self):
        """测试多参数翻译（如果有的话）"""
        set_locale('zh-CN')

        # 测试现有的多参数翻译
        file_translation = t("file_label", filename="test.md")
        self.assertEqual(file_translation, "文件: test.md")

        desc_translation = t("description_label", description="测试描述")
        self.assertEqual(desc_translation, "描述: 测试描述")

        tags_translation = t("tags_label", tags="标签1,标签2")
        self.assertEqual(tags_translation, "标签: 标签1,标签2")

    def test_time_display_format_consistency(self):
        """测试时间显示格式的一致性"""
        # 测试时间格式在不同语言下的一致性
        test_time = "2023-12-25 15:30"

        # 中文
        set_locale('zh-CN')
        zh_time = t("modified_time_label", mtime=test_time)

        # 英文
        set_locale('en')
        en_time = t("modified_time_label", mtime=test_time)

        # 时间格式应该保持一致，只是标签语言不同
        self.assertIn(test_time, zh_time)
        self.assertIn(test_time, en_time)
        self.assertIn("15:30", zh_time)
        self.assertIn("15:30", en_time)

if __name__ == '__main__':
    unittest.main()