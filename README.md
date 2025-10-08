# Hugo 博客发布工具

这是一个用于将 Markdown 文件发布到 Hugo 博客并部署到 GitHub Pages 的工具。

## 功能特性

- 自动处理 Markdown 文件的前置数据（front matter）
- 支持图片处理和 Mermaid 图表转换
- 自动标签到分类的映射
- 支持草稿模式发布
- 支持预览模式
- 支持取消发布文章
- **新增：交互式选择要发布的文章**

## 安装
1. 克隆或下载此仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 复制配置文件模板：`cp config.yaml.example config.yaml`
4. 编辑 `config.yaml` 文件，配置你的路径和仓库信息

## 使用方法

### 基本用法

```bash
# 查看所有可用命令
python hugo_publish_blog.py --help

# 发布文章
python hugo_publish_blog.py publish

# 发布所有已标记为 publish: true 的文章
python hugo_publish_blog.py publish

# 发布特定文件
python hugo_publish_blog.py publish --files article1.md article2.md

# 以草稿模式发布
python hugo_publish_blog.py publish --draft

# 交互式选择文章发布
python hugo_publish_blog.py publish --select
```

### 新增：交互式选择功能

使用 `--select` 参数可以交互式地选择要发布的文章：

```bash
python hugo_publish_blog.py publish --select
```

这将显示所有可发布的文章列表，包括：
- 文章标题
- 文件名
- 描述
- 标签

然后你可以：
- 输入单个数字选择特定文章（如：`0`）
- 输入多个数字用逗号分隔（如：`0,2,5`）
- 输入数字范围（如：`1-3` 选中第1-3篇文章）
- 输入 `all` 选择所有文章
- 留空取消操作

### 其他功能

```bash
# 预览模式（启动 Hugo 服务器）
python hugo_publish_blog.py preview

# 取消发布文章
python hugo_publish_blog.py unpublish

# 重新发布所有文章
python hugo_publish_blog.py republish

# 指定源目录和 Hugo 目录
python hugo_publish_blog.py publish --source /path/to/source --hugo-dir /path/to/hugo

# 输出为 JSON 格式（便于脚本处理）
python hugo_publish_blog.py publish --output-format json
```

## 配置

编辑 `config.yaml` 文件：

```yaml
paths:
  obsidian:
    vault: ~/obsidian-vault
  hugo:
    blog: ~/hugo-blog

repositories:
  source:
    url: git@github.com:username/blog-source.git
  pages:
    url: git@github.com:username/username.github.io.git
```

## 前置数据格式

在你的 Markdown 文件中使用以下格式的前置数据：

```yaml
---
title: 文章标题
date: 2241-1: true
description: 文章描述
tags: [标签1, 标签2]
categories: [分类1, 分类2]
draft: false
---
```

## 注意事项

- 确保已配置 SSH 密钥以访问 GitHub 仓库
- 确保 Hugo 已正确安装
- 文章必须设置 `publish: true` 才会被处理
- 图片路径会自动处理，支持 Obsidian 的 `![[image.jpg]]` 格式

## 项目结构

```
├── hugo_publish_blog.py          # 主程序入口
├── config.yaml.example           # 配置文件示例
├── tag_category_map.yaml.example # 标签分类映射示例
├── upload_image_to_blog.py       # 图片上传脚本（兼容性包装器）
├── config.yaml                   # 配置文件（需自行创建）
├── tag_category_mapping.yaml     # 标签分类映射文件（需自行创建）
├── requirements.txt              # 依赖包列表
├── README.md                     # 项目说明
├── LICENSE                       # 许可证文件
├── src/                          # 源代码目录
│   ├── __init__.py
│   ├── core/                     # 核心模块
│   │   ├── config_manager.py     # 配置管理
│   │   ├── blog_processor.py     # 博客处理
│   │   └── front_matter.py       # 前端数据处理
│   ├── handlers/                 # 处理器模块
│   │   └── obsidian_image_handler.py  # Obsidian图片处理
│   ├── i18n/                     # 国际化模块
│   │   ├── i18n.py              # 国际化功能
│   │   ├── zh-CN.json           # 中文翻译
│   │   └── en.json              # 英文翻译
│   └── utils/                    # 工具模块
│       ├── cli_utils.py         # 命令行工具
│       ├── logger.py            # 日志模块
│       └── utils.py             # 通用工具函数
├── docs/                         # 文档目录
│   ├── DEVELOPMENT.md           # 开发文档
│   ├── API.md                  # API文档
│   └── IMAGE_UPLOAD_GUIDE.md   # 图片上传指南
├── tests/                        # 测试目录
└── venv/                         # Python虚拟环境（如果已创建）
```

## 许可证

MIT License
