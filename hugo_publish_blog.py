# 博客发布脚本
# 用于将Markdown文件发布到Hugo博客并部署到GitHub Pages

import re
from pathlib import Path
import argparse
import subprocess
import os
import shutil
import yaml
from datetime import datetime
import sys

# 添加scripts目录到Python路径
current_dir = Path(__file__).resolve().parent
script_dir = current_dir / 'scripts'
sys.path.insert(0, str(script_dir))

from scripts.obsidian_image_handler import process_obsidian_images

# ANSI 颜色代码
COLOR_GREEN = "\033[92m"    # 成功信息
COLOR_RED = "\033[91m"      # 错误信息
COLOR_YELLOW = "\033[93m"   # 警告和提示
COLOR_BLUE = "\033[94m"     # 步骤和进度
COLOR_BOLD = "\033[1m"      # 粗体
COLOR_DIM = "\033[2m"       # 暗色
COLOR_ITALIC = "\033[3m"    # 斜体
COLOR_UNDERLINE = "\033[4m" # 下划线
COLOR_RESET = "\033[0m"     # 重置颜色
COLOR_CYAN = "\033[96m"     # 信息提示
COLOR_MAGENTA = "\033[95m"  # 强调

# 格式化输出函数
def print_step(step_num, message):
    """打印带编号的步骤信息"""
    print(f"\n{COLOR_BLUE}{COLOR_BOLD}[步骤 {step_num}]{COLOR_RESET} {message}")

def print_success(message):
    """打印成功信息"""
    print(f"{COLOR_GREEN}✓ {message}{COLOR_RESET}")

def print_error(message):
    """打印错误信息"""
    print(f"{COLOR_RED}✗ {message}{COLOR_RESET}")

def print_warning(message):
    """打印警告信息"""
    print(f"{COLOR_YELLOW}! {message}{COLOR_RESET}")

def print_info(message):
    """打印普通信息"""
    print(f"{COLOR_CYAN}ℹ {message}{COLOR_RESET}")

def print_header(message):
    """打印标题信息"""
    print(f"\n{COLOR_MAGENTA}{COLOR_BOLD}{message}{COLOR_RESET}")
    print(f"{COLOR_DIM}{'='*len(message)}{COLOR_RESET}\n")

def extract_yaml_and_content(md_file):
    """从markdown文件中提取YAML头部信息和正文内容"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for YAML front matter
    if not content.startswith('---\n'):
        return None, content
    
    # Find the end of YAML front matter
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return None, content
    
    try:
        yaml_data = yaml.safe_load(parts[1])
        return yaml_data, parts[2]
    except yaml.YAMLError:
        return None, content

def create_new_post(hugo_dir, title, content, source_file=None, categories=None, tags=None, draft=False):
    """创建新的Hugo博客文章"""
    # 创建文章目录和文件
    post_dir = Path(hugo_dir) / 'content' / 'post' / title.lower().replace(' ', '-')
    post_dir.mkdir(parents=True, exist_ok=True)
    
    post_file = post_dir / 'index.md'
    
    # 如果是Obsidian文章，处理图片
    if source_file:
        content = process_obsidian_images(content, source_file, post_dir, Path(source_file).parent)
    
    # 检测文章中的第一张图片
    first_image = None
    # 匹配两种格式的图片
    img_patterns = [
        r'!\[([^\]]*)\]\(([^)]+)\)',  # ![alt](image.jpg)
        r'!\[\[([^]]+)\]\]'  # ![[image.jpg]]
    ]
    for pattern in img_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            if pattern == r'!\[\[([^]]+)\]\]':
                img_name = match.group(1)
            else:
                img_name = match.group(2)
            # 清理图片名称
            img_name = img_name.split('#')[0].split('?')[0].replace('%20', '-')
            first_image = img_name
            break
        if first_image:
            break
    
    # 准备YAML前置数据
    front_matter = {
        'title': title,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'description': f'Content from {title}',
        'draft': draft,  # 添加草稿标记
    }
    
    # 如果找到图片，添加image字段
    if first_image:
        front_matter['image'] = first_image
    
    if categories:
        front_matter['categories'] = categories
    if tags:
        front_matter['tags'] = tags
    
    # 写入文件
    with open(post_file, 'w', encoding='utf-8') as f:
        f.write('---\n')
        yaml.dump(front_matter, f, allow_unicode=True)
        f.write('---\n\n')
        f.write(content)
    
    return post_file

def process_markdown_files(source_dir, hugo_dir, selected_files=None, as_draft=False):
    """处理Markdown文件并创建Hugo博客文章"""
    processed_files = []
    source_dir = Path(source_dir)
    hugo_dir = Path(hugo_dir)
    
    # 查找所有Markdown文件
    for md_file in source_dir.rglob('*.md'):
        # 如果指定了文件列表且当前文件不在其中，则跳过
        if selected_files and md_file.name not in selected_files:
            continue
            
        # 提取YAML和内容
        yaml_data, content = extract_yaml_and_content(md_file)
        
        # 如果没有YAML或publish不为true，则跳过
        if not yaml_data or not yaml_data.get('publish', False):
            print_warning(f"跳过 {md_file.name} - 未标记为发布状态")
            continue
        
        # 创建新的博客文章
        try:
            title = md_file.stem
            categories = yaml_data.get('categories', [])
            tags = yaml_data.get('tags', [])
            
            new_post = create_new_post(
                hugo_dir,
                title,
                content,
                source_file=md_file,
                categories=categories,
                tags=tags,
                draft=as_draft
            )
            print_success(f"已创建新文章: {new_post}")
            processed_files.append(new_post)
            
        except Exception as e:
            print_error(f"处理 {md_file.name} 时出错: {str(e)}")
    
    return processed_files

def deploy_to_repos(hugo_dir, repo_source, repo_pages, commit_msg=None):
    """使用SSH部署更改到源码仓库和页面仓库"""
    try:

        # 1. Setup .gitignore for Hugo site
        gitignore_path = hugo_dir / '.gitignore'
        if not gitignore_path.exists():
            with open(gitignore_path, 'w') as f:
                f.write("public/\n.DS_Store\nresources/\n")
        
        # 2. Deploy to source repository
        print(f"\n{COLOR_YELLOW}执行部署流程...{COLOR_RESET}")
        # Switch to main branch and pull latest changes
        subprocess.run(['git', 'checkout', 'main'], cwd=hugo_dir, check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], cwd=hugo_dir, check=True)
        
        # Remove public directory from git if it's tracked
        subprocess.run(['git', 'rm', '-r', '--cached', 'public'], cwd=hugo_dir, stderr=subprocess.DEVNULL, check=False)
        # Add all changes except public directory
        subprocess.run(['git', 'add', '-A'], cwd=hugo_dir, check=True)
        
        # Check if there are changes to commit
        result = subprocess.run(['git', 'status', '--porcelain'], cwd=hugo_dir, capture_output=True, text=True)
        if result.stdout.strip():
            # Allow empty commits and use provided commit message
            commit_msg = commit_msg or "Update blog content"
            subprocess.run(['git', 'commit', '-m', commit_msg, '--allow-empty'], cwd=hugo_dir, check=True)
        # Set correct remote URL and push
        subprocess.run(['git', 'remote', 'set-url', 'origin', repo_source], cwd=hugo_dir, check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=hugo_dir, check=True)
        print_success("源码仓库更新成功！")

        # 构建Hugo站点
        print_step(2, "构建Hugo站点...")
        subprocess.run(['hugo', '--minify'], cwd=hugo_dir, check=True)

        # 部署到页面仓库
        public_dir = hugo_dir / 'public'
        print_step(3, "部署到GitHub Pages仓库...")
        
        # 如果需要，初始化public目录
        if not (public_dir / '.git').exists():
            subprocess.run(['git', 'init'], cwd=public_dir, check=True)
            subprocess.run(['git', 'remote', 'add', 'origin', repo_pages], cwd=public_dir, check=True)
        else:
            subprocess.run(['git', 'remote', 'set-url', 'origin', repo_pages], cwd=public_dir, check=True)
        
        # Commit and push changes to pages repository
        subprocess.run(['git', 'add', '.'], cwd=public_dir, check=True)
        pages_msg = f"Deploy website: {commit_msg}" if commit_msg else "Update website"
        subprocess.run(['git', 'commit', '-m', pages_msg, '--allow-empty'], cwd=public_dir, check=True)
        subprocess.run(['git', 'push', 'origin', 'main', '--force'], cwd=public_dir, check=True)
        print_success("GitHub Pages 部署成功！")
        print(f"\n{COLOR_GREEN}全部部署流程已完成！{COLOR_RESET}")
        
    except subprocess.CalledProcessError as e:
        print_error(f"Deployment failed: {str(e)}")
        return False
    return True

def list_published_markdowns(source_dir):
    """列出所有publish: true的markdown文件"""
    published = []
    for md_file in Path(source_dir).rglob('*.md'):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                yaml_data = yaml.safe_load(parts[1])
                if yaml_data and yaml_data.get('publish', False):
                    published.append((md_file, yaml_data))
    return published

def set_publish_false(md_file):
    """将markdown文件的publish字段设为false"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    if not content.startswith('---\n'):
        return False
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return False
    yaml_data = yaml.safe_load(parts[1])
    if not yaml_data or not yaml_data.get('publish', False):
        return False
    yaml_data['publish'] = False
    new_yaml = yaml.dump(yaml_data, allow_unicode=True)
    new_content = f"---\n{new_yaml}---\n{parts[2]}"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def unpublish_article(hugo_dir, article_name):
    """删除hugo下对应文章文件夹"""
    post_dir = Path(hugo_dir) / 'content' / 'post' / article_name.lower().replace(' ', '-')
    if post_dir.exists():
        shutil.rmtree(post_dir)
        print(f"{COLOR_YELLOW}已删除Hugo文章: {post_dir}{COLOR_RESET}")
        return True
    return False

def preview_site(hugo_dir):
    """启动Hugo服务器预览站点"""
    try:
        print_info("正在启动Hugo服务器进行预览...")
        # 使用subprocess.Popen来启动后台进程
        preview_process = subprocess.Popen(
            ['hugo', 'server', '--buildDrafts', '--buildFuture'],
            cwd=hugo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 等待服务器启动
        import time
        time.sleep(2)
        
        # 检查服务器是否成功启动
        if preview_process.poll() is None:
            print_success("预览服务器已启动！")
            print_info("请访问 http://localhost:1313 查看预览")
            print_info("按 Ctrl+C 停止预览...")
            try:
                preview_process.wait()
            except KeyboardInterrupt:
                preview_process.terminate()
                print_info("\n预览服务器已停止")
        else:
            stdout, stderr = preview_process.communicate()
            print_error(f"预览服务器启动失败: {stderr}")
    except Exception as e:
        print_error(f"启动预览服务器时出错: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='将Markdown文件发布到Hugo博客')
    parser.add_argument('--source', 
                       default='~/Documents/Obsidian Vault/',
                       help='包含markdown文件的源目录')
    parser.add_argument('--hugo-dir',
                       default='~/github_pages/blog',
                       help='Hugo博客目录')
    parser.add_argument('--files',
                       nargs='*',
                       help='要处理的特定markdown文件（可选）')
    parser.add_argument('--unpublish', action='store_true', help='取消发布模式')
    parser.add_argument('--preview', action='store_true', help='预览模式，启动Hugo服务器')
    parser.add_argument('--draft', action='store_true', help='以草稿模式发布文章')
    parser.add_argument('--republish', action='store_true', help='取消所有发布的文章并重新发布')
    
    args = parser.parse_args()
    
    source_dir = Path(args.source).expanduser()
    hugo_dir = Path(args.hugo_dir).expanduser()
    
    if not source_dir.exists():
        print_error(f"错误：源目录 {source_dir} 不存在")
        return
    
    if not hugo_dir.exists():
        print_error(f"错误：Hugo目录 {hugo_dir} 不存在")
        return
    
    if args.preview:
        preview_site(hugo_dir)
        return

    if args.republish:
        # 1. 找出所有已发布的文章
        print_header("开始重新发布所有文章")
        published = list_published_markdowns(source_dir)
        if not published:
            print_warning("没有已发布的文章")
            return
            
        # 2. 取消所有文章的发布
        print_step(1, "取消所有文章的发布")
        for md_file, _ in published:
            article_name = Path(md_file).stem
            if unpublish_article(hugo_dir, article_name):
                print_success(f"已取消发布: {article_name}")
                
        # 3. 重新发布所有文章
        print_step(2, "重新发布所有文章")
        processed_files = process_markdown_files(
            source_dir,
            hugo_dir,
            as_draft=args.draft
        )
        
        if not processed_files:
            print_warning("没有处理任何文件")
            return
            
        print_success(f"成功处理了 {len(processed_files)} 个文件")
        
        # 4. 部署到仓库
        print_step(3, "部署到远程仓库")
        commit_msg = "重新发布所有文章"
        repo_source = 'git@github.com:MciG-ggg/hugo_blog.git'
        repo_pages = 'git@github.com:MciG-ggg/MciG-ggg.github.io.git'
        if deploy_to_repos(hugo_dir, repo_source, repo_pages, commit_msg):
            print_success("所有文章已重新发布并部署")
        return

    if args.unpublish:
        published = list_published_markdowns(source_dir)
        if not published:
            print_warning(f"没有已发布的文章可取消")
            return
        print(f"{COLOR_YELLOW}已发布的文章列表：{COLOR_RESET}")
        for idx, (md_file, yaml_data) in enumerate(published):
            print(f"[{idx}] {md_file}")
        idxs = input(f"请输入要取消发布的编号（可用逗号分隔，留空取消）：").strip()
        if not idxs:
            print_warning(f"未选择任何文章，操作取消")
            return
        idxs = [int(i) for i in idxs.split(',') if i.strip().isdigit() and int(i) < len(published)]
        for i in idxs:
            md_file, yaml_data = published[i]
            set_publish_false(md_file)
            article_name = Path(md_file).stem
            unpublish_article(hugo_dir, article_name)
        # git操作
        repo_source = 'git@github.com:MciG-ggg/hugo_blog.git'
        print(f"{COLOR_YELLOW}推送到远端...{COLOR_RESET}")
        commit_msg = input(f"请输入取消发布的提交信息: ").strip() or "Unpublish articles"
        deploy_to_repos(hugo_dir, repo_source, repo_pages='git@github.com:MciG-ggg/MciG-ggg.github.io.git', commit_msg=commit_msg)
        return
    
    # 处理文件
    processed_files = process_markdown_files(
        source_dir, 
        hugo_dir, 
        args.files,
        as_draft=args.draft
    )
    
    if not processed_files:
        print_warning(f"没有处理任何文件")
        return
    
    print_success(f"成功处理了 {len(processed_files)} 个文件")
    
    # Deploy to repositories
    if input(f"\n{COLOR_YELLOW}是否要部署更改？[y/N]: {COLOR_RESET}").lower().strip() in ('y', 'yes'):
        # Check if SSH key is configured
        try:
            subprocess.run(['ssh', '-T', 'git@github.com'], 
                         stderr=subprocess.PIPE, 
                         stdout=subprocess.PIPE, 
                         check=False)
        except Exception as e:
            print_error(f"SSH 连接测试失败，请确保已配置 SSH 密钥：{str(e)}")
            return

        # Get commit message
        commit_msg = input(f"\n{COLOR_YELLOW}请输入提交信息: {COLOR_RESET}").strip()
        if not commit_msg:
            print_error(f"提交信息不能为空")
            return

        # Show deployment plan
        print(f"\n{COLOR_YELLOW}即将执行以下操作：{COLOR_RESET}")
        print(f"1. 切换到main分支并拉取最新代码")
        print(f"2. 添加所有更改到Git")
        print(f'3. 提交信息: "{commit_msg}"')
        print(f"4. 推送到源码仓库")
        print(f"5. 构建Hugo站点")
        print(f"6. 部署到GitHub Pages")
        
        if input(f"\n{COLOR_YELLOW}确认执行以上操作？[y/N]: {COLOR_RESET}").lower().strip() not in ('y', 'yes'):
            print_error(f"部署已取消")
            return
        
        repo_source = 'git@github.com:MciG-ggg/hugo_blog.git'
        repo_pages = 'git@github.com:MciG-ggg/MciG-ggg.github.io.git'
        deploy_to_repos(hugo_dir, repo_source, repo_pages, commit_msg)

if __name__ == '__main__':
    main()
