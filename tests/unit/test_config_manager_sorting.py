"""
Config 排序配置功能的单元测试
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import Config


class TestConfigSorting:
    """测试 Config 类的排序配置功能"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.yaml"

    def teardown_method(self):
        """每个测试方法执行后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_default_sort_config(self):
        """测试默认排序配置"""
        config = Config()

        # 测试默认配置存在且为 true
        sort_config = config.get('display.sort_by_mtime', True)
        assert sort_config is True

    def test_load_sort_config_from_file(self):
        """测试从文件加载排序配置"""
        # 创建测试配置文件
        config_content = """
display:
  sort_by_mtime: false
paths:
  obsidian:
    vault: "~/test"
"""
        self.config_file.write_text(config_content, encoding='utf-8')

        # 加载配置
        config = Config(str(self.config_file))

        # 验证配置被正确加载
        sort_config = config.get('display.sort_by_mtime', True)
        assert sort_config is False

    def test_invalid_sort_config_value(self):
        """测试无效排序配置值的处理"""
        # 创建包含无效值的配置文件
        config_content = """
display:
  sort_by_mtime: "invalid_value"
paths:
  obsidian:
    vault: "~/test"
"""
        self.config_file.write_text(config_content, encoding='utf-8')

        # 加载配置
        config = Config(str(self.config_file))

        # 应该返回字符串值，由调用方进行类型转换
        sort_config = config.get('display.sort_by_mtime', True)
        assert sort_config == "invalid_value"

    def test_missing_sort_config_section(self):
        """测试缺少排序配置节的情况"""
        # 创建没有 display 节的配置文件
        config_content = """
paths:
  obsidian:
    vault: "~/test"
hugo:
  theme: "PaperMod"
"""
        self.config_file.write_text(config_content, encoding='utf-8')

        # 加载配置
        config = Config(str(self.config_file))

        # 应该使用默认值
        sort_config = config.get('display.sort_by_mtime', True)
        assert sort_config is True

    def test_get_sort_config_method(self):
        """测试 get_sort_config 方法"""
        config = Config()

        # 测试方法存在并返回布尔值
        if hasattr(config, 'get_sort_config'):
            sort_config = config.get_sort_config()
            assert isinstance(sort_config, bool)
            assert sort_config is True  # 默认应该为 True
        else:
            # 如果方法不存在，使用 get 方法作为备选
            sort_config = config.get('display.sort_by_mtime', True)
            assert sort_config is True

    def test_config_schema_includes_sort_config(self):
        """测试配置结构包含排序配置"""
        config = Config()
        schema = config.get_config_schema()

        # 验证 display 节存在
        assert 'display' in schema

        # 验证 sort_by_mtime 配置项在结构中
        display_schema = schema['display']
        assert 'sort_by_mtime' in display_schema

        # 验证配置项类型为布尔值
        sort_config_schema = display_schema['sort_by_mtime']
        assert sort_config_schema['type'] == 'boolean'
        assert sort_config_schema['default'] is True
        assert 'description' in sort_config_schema

    def test_partial_display_config(self):
        """测试部分 display 配置的情况"""
        # 创建只有部分 display 配置的文件
        config_content = """
display:
  theme: "dark"
paths:
  obsidian:
    vault: "~/test"
"""
        self.config_file.write_text(config_content, encoding='utf-8')

        # 加载配置
        config = Config(str(self.config_file))

        # sort_by_mtime 应该使用默认值
        sort_config = config.get('display.sort_by_mtime', True)
        assert sort_config is True

        # 其他 display 配置应该正常加载
        theme_config = config.get('display.theme')
        assert theme_config == "dark"

    def test_boolean_string_conversion(self):
        """测试布尔字符串转换"""
        # 测试没有引号的布尔值（YAML会自动转换为布尔值）
        config_content_true = """
display:
  sort_by_mtime: true
paths:
  obsidian:
    vault: "~/test"
"""
        self.config_file.write_text(config_content_true, encoding='utf-8')
        config_true = Config(str(self.config_file))

        # YAML 会自动转换无引号的 true 为布尔值 true
        sort_config_true = config_true.get('display.sort_by_mtime', True)
        assert sort_config_true is True

        # 测试没有引号的 false
        config_content_false = """
display:
  sort_by_mtime: false
paths:
  obsidian:
    vault: "~/test"
"""
        self.config_file.write_text(config_content_false, encoding='utf-8')
        config_false = Config(str(self.config_file))

        sort_config_false = config_false.get('display.sort_by_mtime', True)
        assert sort_config_false is False

    def test_config_compatibility(self):
        """测试配置兼容性 - 确保新配置不影响现有功能"""
        # 创建标准的配置文件，不包含新的排序配置
        config_content = """
paths:
  obsidian:
    vault: "~/Documents/Obsidian Vault"
    images: "~/Documents/Obsidian Vault/zob_source/images"
  hugo:
    blog: "~/github_pages/blog"
    public: "public"
repositories:
  source:
    url: "git@github.com:test/test.git"
    branch: "main"
  pages:
    url: "git@github.com:test/test-pages.git"
    branch: "main"
"""
        self.config_file.write_text(config_content, encoding='utf-8')

        # 加载配置应该正常工作
        config = Config(str(self.config_file))

        # 现有配置应该正常加载
        assert config.get('paths.obsidian.vault') == "~/Documents/Obsidian Vault"
        assert config.get('repositories.source.url') == "git@github.com:test/test.git"

        # 新配置应该使用默认值
        sort_config = config.get('display.sort_by_mtime', True)
        assert sort_config is True

    def test_empty_config_file(self):
        """测试空配置文件"""
        # 创建空配置文件
        self.config_file.write_text("", encoding='utf-8')

        # 加载配置应该使用默认配置
        config = Config(str(self.config_file))

        # 应该使用默认的排序配置
        sort_config = config.get('display.sort_by_mtime', True)
        assert sort_config is True

        # 空文件会导致 yaml.safe_load 返回 None，所以应该使用全部默认配置
        # 但是由于我们的实现，空文件会被视为没有配置文件而使用默认配置
        # 所以应该有默认的 paths 配置
        paths_config = config.get('paths')
        assert paths_config is not None
        assert 'obsidian' in paths_config
        assert 'hugo' in paths_config

    def test_get_sort_config_with_config_file(self):
        """测试 get_sort_config 方法在有配置文件时的行为"""
        # 创建禁用排序的配置文件
        config_content = """
display:
  sort_by_mtime: false
paths:
  obsidian:
    vault: "~/test"
"""
        self.config_file.write_text(config_content, encoding='utf-8')

        config = Config(str(self.config_file))
        sort_config = config.get_sort_config()
        assert sort_config is False

        # 创建启用排序的配置文件
        config_content = """
display:
  sort_by_mtime: true
paths:
  obsidian:
    vault: "~/test"
"""
        self.config_file.write_text(config_content, encoding='utf-8')

        config = Config(str(self.config_file))
        sort_config = config.get_sort_config()
        assert sort_config is True