#!/usr/bin/env python3
"""
配置管理模块
用于加载和管理博客发布工具的配置
"""

import yaml
from pathlib import Path
import os
from typing import Dict, Any

class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器
        :param config_file: 配置文件路径，如果为None则使用默认路径
        """
        self.config_file = config_file or str(Path(__file__).parent.parent / 'config.yaml')
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        :return: 配置字典
        """
        if not Path(self.config_file).exists():
            return self._get_default_config()
            
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
            
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        :return: 默认配置字典
        """
        return {
            'paths': {
                'obsidian': {
                    'vault': '~/Documents/Obsidian Vault/',
                    'images': '~/Documents/Obsidian Vault/zob_source/images'
                },
                'hugo': {
                    'blog': '~/github_pages/blog',
                    'public': 'public'
                }
            },
            'repositories': {
                'source': {
                    'url': 'git@github.com:MciG-ggg/hugo_blog.git',
                    'branch': 'main'
                },
                'pages': {
                    'url': 'git@github.com:MciG-ggg/MciG-ggg.github.io.git',
                    'branch': 'main'
                }
            },
            'images': {
                'optimize': False,
                'max_width': 1920,
                'quality': 85,
                'generate_thumbnail': False,
                'thumbnail_width': 400
            },
            'posts': {
                'auto_summary': False,
                'summary_length': 200,
                'link_related': False,
                'related_count': 5
            },
            'hugo': {
                'theme': 'PaperMod',
                'baseURL': 'https://mcig-ggg.github.io/'
            },
            'deployment': {
                'backup': False,
                'check_links': False,
                'minify': True
            }
        }
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        :param key: 配置键，支持点号分隔的多级键
        :param default: 默认值
        :return: 配置值
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
        
    def save(self) -> None:
        """
        保存配置到文件
        """
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True)
            
    def update(self, key: str, value: Any) -> None:
        """
        更新配置
        :param key: 配置键，支持点号分隔的多级键
        :param value: 新的配置值
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()
        
    def expand_path(self, path: str) -> str:
        """
        展开路径中的用户目录和环境变量
        :param path: 原始路径
        :return: 展开后的路径
        """
        return os.path.expandvars(os.path.expanduser(path))
