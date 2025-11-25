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
        if config_file:
            self.config_file = config_file
        else:
            # Look for config.yaml in the project root directory
            # config_manager.py is at: project_root/src/core/config_manager.py
            # So we need to go up 2 levels: src/core -> src -> project_root
            project_root = Path(__file__).parent.parent.parent  # Going up three levels to project root
            self.config_file = str(project_root / 'config.yaml')

        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        :return: 配置字典
        """
        if not Path(self.config_file).exists():
            return self._get_default_config()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
                # 如果文件为空或内容为null，返回默认配置
                if loaded_config is None:
                    return self._get_default_config()
                return loaded_config
        except (yaml.YAMLError, IOError) as e:
            # 如果配置文件解析失败，使用默认配置
            print(f"Warning: Failed to load config file {self.config_file}: {e}")
            return self._get_default_config()

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
            },
            'display': {
                'sort_by_mtime': True
            },
            'api': {
                'deepseek': {
                    'api_key': '',
                    'base_url': 'https://api.deepseek.com',
                    'model': 'deepseek-chat'
                }
            },
            'logging': {
                'level': 'INFO',
                'file': '',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

    def get_sort_config(self) -> bool:
        """
        获取排序配置
        :return: 是否启用按修改时间排序
        """
        return bool(self.get('display.sort_by_mtime', True))

    def expand_path(self, path: str) -> str:
        """
        展开路径中的用户目录和环境变量
        :param path: 原始路径
        :return: 展开后的路径
        """
        return os.path.expandvars(os.path.expanduser(path))

    def validate_config(self) -> bool:
        """
        验证配置的有效性
        :return: 配置是否有效
        """
        # 检查必要路径是否存在
        obsidian_vault = self.get('paths.obsidian.vault')
        hugo_blog = self.get('paths.hugo.blog')

        if not obsidian_vault or not hugo_blog:
            print_error("配置错误：必须设置 obsidian.vault 和 hugo.blog 路径")
            return False

        # 检查仓库URL
        source_url = self.get('repositories.source.url')
        pages_url = self.get('repositories.pages.url')

        if not source_url or not pages_url:
            print_error("配置错误：必须设置 source 和 pages 仓库URL")
            return False

        # 检查路径是否存在
        expanded_obsidian = self.expand_path(obsidian_vault)
        expanded_hugo = self.expand_path(hugo_blog)

        if not Path(expanded_obsidian).exists():
            print_error(f"配置错误：Obsidian仓库路径不存在: {expanded_obsidian}")
            return False

        if not Path(expanded_hugo).exists():
            print_error(f"配置错误：Hugo博客路径不存在: {expanded_hugo}")
            return False

        return True

    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取配置结构模式，用于验证和文档
        :return: 配置结构模式
        """
        return {
            'paths': {
                'obsidian': {
                    'vault': {'type': 'string', 'required': True, 'description': 'Obsidian仓库路径'},
                    'images': {'type': 'string', 'required': False, 'description': '图片存储路径'}
                },
                'hugo': {
                    'blog': {'type': 'string', 'required': True, 'description': 'Hugo博客目录'},
                    'public': {'type': 'string', 'required': False, 'description': '生成的静态文件目录'}
                }
            },
            'repositories': {
                'source': {
                    'url': {'type': 'string', 'required': True, 'description': '源码仓库URL'},
                    'branch': {'type': 'string', 'required': False, 'default': 'main', 'description': '分支名称'}
                },
                'pages': {
                    'url': {'type': 'string', 'required': True, 'description': '页面仓库URL'},
                    'branch': {'type': 'string', 'required': False, 'default': 'main', 'description': '分支名称'}
                }
            },
            'images': {
                'optimize': {'type': 'boolean', 'required': False, 'default': False, 'description': '是否优化图片'},
                'max_width': {'type': 'integer', 'required': False, 'default': 1920, 'description': '最大宽度'},
                'quality': {'type': 'integer', 'required': False, 'default': 85, 'description': '图片质量(1-100)'},
                'generate_thumbnail': {'type': 'boolean', 'required': False, 'default': False, 'description': '是否生成缩略图'},
                'thumbnail_width': {'type': 'integer', 'required': False, 'default': 400, 'description': '缩略图宽度'}
            },
            'posts': {
                'auto_summary': {'type': 'boolean', 'required': False, 'default': False, 'description': '是否自动生成摘要'},
                'summary_length': {'type': 'integer', 'required': False, 'default': 200, 'description': '摘要长度'},
                'link_related': {'type': 'boolean', 'required': False, 'default': False, 'description': '是否链接相关文章'},
                'related_count': {'type': 'integer', 'required': False, 'default': 5, 'description': '相关文章数量'}
            },
            'hugo': {
                'theme': {'type': 'string', 'required': False, 'default': 'PaperMod', 'description': '主题名称'},
                'baseURL': {'type': 'string', 'required': False, 'default': 'https://username.github.io/', 'description': '网站基础URL'}
            },
            'deployment': {
                'backup': {'type': 'boolean', 'required': False, 'default': False, 'description': '是否在部署前备份'},
                'check_links': {'type': 'boolean', 'required': False, 'default': False, 'description': '是否检查链接'},
                'minify': {'type': 'boolean', 'required': False, 'default': True, 'description': '是否压缩HTML/CSS/JS'}
            },
            'display': {
                'sort_by_mtime': {
                    'type': 'boolean',
                    'required': False,
                    'default': True,
                    'description': '是否按修改时间排序文章列表'
                }
            },
            'api': {
                'deepseek': {
                    'api_key': {'type': 'string', 'required': False, 'description': 'DeepSeek API密钥'},
                    'base_url': {'type': 'string', 'required': False, 'default': 'https://api.deepseek.com', 'description': 'API基础URL'},
                    'model': {'type': 'string', 'required': False, 'default': 'deepseek-chat', 'description': '使用的模型名称'}
                }
            },
            'logging': {
                'level': {'type': 'string', 'required': False, 'default': 'INFO', 'description': '日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)'},
                'file': {'type': 'string', 'required': False, 'default': '', 'description': '日志文件路径'},
                'format': {'type': 'string', 'required': False, 'default': '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 'description': '日志格式'}
            }
        }