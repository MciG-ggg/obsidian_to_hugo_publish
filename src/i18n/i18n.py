"""
国际化（i18n）模块
提供多语言支持功能
"""

import json
import os
from pathlib import Path


class I18n:
    """
    国际化类，提供多语言支持
    """
    
    def __init__(self, locale='zh-CN', fallback_locale='en'):
        """
        初始化国际化类
        :param locale: 当前语言环境
        :param fallback_locale: 后备语言环境
        """
        # 标准化语言代码
        self.locale = self._normalize_locale(locale)
        self.fallback_locale = self._normalize_locale(fallback_locale)
        self.translations = {}
        self.fallback_translations = {}

        # 加载翻译文件
        self._load_translations()

    def _normalize_locale(self, locale):
        """
        标准化语言代码，处理常见的映射关系
        :param locale: 原始语言代码
        :return: 标准化后的语言代码
        """
        if not locale:
            return 'zh-CN'  # 默认中文

        # 常见语言代码映射
        locale_mappings = {
            'en_US': 'en',
            'en_GB': 'en',
            'en-US': 'en',
            'en-GB': 'en',
            'zh_CN': 'zh-CN',
            'zh_CN.UTF-8': 'zh-CN',
            'zh-CN.UTF-8': 'zh-CN',
            'zh_TW': 'zh-TW',
            'zh-TW': 'zh-TW',
        }

        return locale_mappings.get(locale, locale)

    def _load_translations(self):
        """
        加载翻译文件，支持多种文件名格式
        """
        i18n_dir = Path(__file__).parent / 'translations'

        # 尝试加载当前语言翻译
        locale_files_to_try = [
            f'{self.locale}.json',
            f'{self.locale.split("_")[0]}.json',  # 处理 en_US -> en
            f'{self.locale.split("-")[0]}.json',  # 处理 zh-CN -> zh
        ]

        loaded = False
        for locale_file_name in locale_files_to_try:
            locale_file = i18n_dir / locale_file_name
            if locale_file.exists():
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                loaded = True
                break

        # 后备语言加载逻辑
        fallback_files_to_try = [
            f'{self.fallback_locale}.json',
            f'{self.fallback_locale.split("_")[0]}.json',
            f'{self.fallback_locale.split("-")[0]}.json',
        ]

        fallback_loaded = False
        for fallback_file_name in fallback_files_to_try:
            fallback_file = i18n_dir / fallback_file_name
            if fallback_file.exists():
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    self.fallback_translations = json.load(f)
                fallback_loaded = True
                break

        # 只有在无法加载当前语言且后备语言可用时才显示警告
        if not loaded and fallback_loaded:
            print(f"警告: 找不到 {self.locale} 的翻译文件，将使用后备语言")
        elif not loaded and not fallback_loaded:
            print(f"警告: 找不到 {self.locale} 或 {self.fallback_locale} 的翻译文件")
    
    def t(self, key, **kwargs):
        """
        获取翻译文本
        :param key: 翻译键
        :param kwargs: 用于格式化的参数
        :return: 翻译后的文本
        """
        # 首先尝试当前语言
        if key in self.translations:
            text = self.translations[key]
        # 如果当前语言没有，则尝试后备语言
        elif key in self.fallback_translations:
            text = self.fallback_translations[key]
        # 如果都没有，则返回键本身
        else:
            return key
        
        # 格式化文本
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                print(f"警告: 格式化翻译文本时出错，键: {key}")
        
        return text


# 创建全局实例
i18n_instance = I18n()


def t(key, **kwargs):
    """
    全局翻译函数
    :param key: 翻译键
    :param kwargs: 用于格式化的参数
    :return: 翻译后的文本
    """
    return i18n_instance.t(key, **kwargs)


def set_locale(locale):
    """
    设置语言环境
    :param locale: 语言环境
    """
    global i18n_instance
    i18n_instance = I18n(locale=locale)