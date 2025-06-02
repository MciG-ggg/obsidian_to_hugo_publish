# 📚 Obsidian to Hugo Publisher

这是一个用于将 Obsidian 笔记发布到 Hugo 博客的 Python 工具。

## ✨ 功能特点

- 🔄 自动将 Obsidian 笔记转换为 Hugo 博客文章
- 🖼️ 支持 Obsidian 图片自动处理和迁移
- 📝 支持 YAML front matter 处理
- 📋 支持草稿模式发布
- ❌ 支持文章取消发布
- 🔍 支持博客预览
- 🚀 自动部署到 GitHub Pages
- 🔒 安全的配置管理，避免敏感信息泄露

## 🛠️ 使用方法

### 📌 基本命令

```bash
python hugo_publish_blog.py [options]
```

### 🔧 可用选项

- `--source`: 指定 Obsidian 笔记源目录 (默认使用配置文件中的路径)
- `--hugo-dir`: 指定 Hugo 博客目录 (默认使用配置文件中的路径)
- `--files`: 指定要处理的特定 markdown 文件
- `--unpublish`: 取消发布模式
- `--preview`: 预览模式，启动 Hugo 服务器
- `--draft`: 以草稿模式发布文章
- `--republish`: 取消所有发布的文章并重新发布

所有的默认路径和仓库配置都在 `config.yaml` 中设置，这样可以避免在代码中暴露个人信息。

### 发布流程

1. 在 Obsidian 笔记的 YAML front matter 中设置 `publish: true`
2. 运行脚本发布文章
3. 自动处理图片和其他资源
4. 自动部署到 GitHub Pages

### 示例

发布单篇文章：
```bash
python hugo_publish_blog.py --files article.md
```

预览博客：
```bash
python hugo_publish_blog.py --preview
```

取消发布：
```bash
python hugo_publish_blog.py --unpublish
```

## ⚙️ 安装和配置

1. 📥 克隆仓库：
```bash
git clone https://github.com/MciG-ggg/obsidian_to_hugo_publish.git
cd obsidian_to_hugo_publish
```

2. 📦 安装依赖：
```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

3. 📋 创建配置文件：
```bash
cp config.yaml.example config.yaml
```

4. ✏️ 编辑 config.yaml，填入你的个人配置：
   - 设置 Obsidian 仓库路径
   - 设置 Hugo 博客目录
   - 配置 Git 仓库信息
   - 设置其他选项

5. 🔐 配置 SSH 密钥：
   确保已经配置了 GitHub SSH 密钥，用于自动部署

注意：实际的 config.yaml 不会被提交到git仓库中，以保护你的私人信息。

## 📦 依赖

- 🐍 Python 3.9+
- 📄 PyYAML
- 🌐 Hugo

## 🔐 安全性说明

为了保护您的隐私和安全：

1. 所有个人配置（路径、仓库地址等）都保存在 `config.yaml` 中
2. `config.yaml` 已被添加到 `.gitignore`，不会被提交到 git 仓库
3. 使用 `config.yaml.example` 作为配置模板
4. 建议使用环境变量存储特别敏感的信息
5. 确保不要意外提交包含个人信息的文件

## 📁 目录结构

```
.
├── hugo_publish_blog.py   # 主程序
└── scripts/              # 辅助脚本
    ├── __init__.py
    ├── image_processor.py         # 图片处理模块
    └── obsidian_image_handler.py  # Obsidian图片处理器
```

## ⚠️ 注意事项

1. 确保已正确配置 Hugo 环境
2. 确保已配置 GitHub SSH 密钥
3. 确保源目录和目标目录路径正确

## 许可证

MIT License
