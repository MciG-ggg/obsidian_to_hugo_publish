# Hugo Blog Publisher 🚀

一个用于将 Obsidian 笔记转换为 Hugo 博客文章并自动部署的工具。

## 功能特点 ✨

- 📝 自动将 Obsidian 笔记转换为 Hugo 文章
- 🖼️ 智能处理图片资源
- 🏷️ 自动维护标签和分类映射
- 📋 支持草稿模式
- 🚀 一键部署到 GitHub Pages
- 👀 支持预览模式

## 项目结构 📁

```
.
├── hugo_publish_blog.py   # 主程序
├── config.yaml.example   # 配置文件模板
├── tag_category_map.example 
├── requirements.txt      # 依赖清单
└── scripts/             # 功能模块
    ├── __init__.py
    ├── blog_processor.py        # 博客处理核心类
    ├── front_matter.py          # 文章前置数据处理
    ├── config_manager.py        # 配置管理
    ├── image_processor.py       # 图片处理
    └── obsidian_image_handler.py # Obsidian图片转换
```

## 安装 🔧

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/hugo_publish.git
cd hugo_publish
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置：
```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml 文件，设置你的配置
```

## 使用方法 📖

### 基本命令

1. 发布文章：
```bash
python hugo_publish_blog.py
```

2. 预览站点：
```bash
python hugo_publish_blog.py --preview
```

3. 取消发布：
```bash
python hugo_publish_blog.py --unpublish
```

4. 重新发布所有文章：
```bash
python hugo_publish_blog.py --republish
```

### 配置说明 ⚙️

在 `config.yaml` 中配置以下内容：

```yaml
paths:
  obsidian: "你的Obsidian笔记目录"
  hugo: "你的Hugo博客目录"

repositories:
  source: "源码仓库地址"
  pages: "GitHub Pages仓库地址"

images:
  source_dir: "图片源目录"
  target_dir: "图片目标目录"
```

## 开发说明 💻

### 核心类

1. `BlogProcessor`：处理博客发布的核心类
   - 创建新文章
   - 处理 Markdown 文件
   - 管理发布状态
   - 部署到仓库

2. `FrontMatter`：管理文章前置数据
   - 处理 YAML 头部
   - 管理标签和分类
   - 提供标准化的数据访问接口

### 工作流程 🔄

1. 文章处理流程：
   - 读取 Obsidian 笔记
   - 提取前置数据
   - 处理图片资源
   - 创建 Hugo 文章

2. 部署流程：
   - 更新源码仓库
   - 构建 Hugo 站点
   - 部署到 GitHub Pages

## 贡献 🤝

欢迎提交 Issue 和 Pull Request！

## 许可证 📄

MIT License
