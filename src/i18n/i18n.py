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
        self.locale = locale
        self.fallback_locale = fallback_locale
        self.translations = {}
        self.fallback_translations = {}
        
        # 加载翻译文件
        self._load_translations()
    
    def _load_translations(self):
        """
        加载翻译文件
        """
        # 确定翻译文件路径
        i18n_dir = Path(__file__).parent.parent / 'i18n'
        
        # 加载当前语言的翻译
        locale_file = i18n_dir / f'{self.locale}.json'
        if locale_file.exists():
            with open(locale_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        else:
            print(f"警告: 找不到 {self.locale} 的翻译文件，将使用后备语言")
        
        # 加载后备语言的翻译
        fallback_file = i18n_dir / f'{self.fallback_locale}.json'
        if fallback_file.exists():
            with open(fallback_file, 'r', encoding='utf-8') as f:
                self.fallback_translations = json.load(f)
        else:
            print(f"警告: 找不到 {self.fallback_locale} 的翻译文件")
    
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