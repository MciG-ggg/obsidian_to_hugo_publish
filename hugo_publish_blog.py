# 博客发布脚本
# 用于将Markdown文件发布到Hugo博客并部署到GitHub Pages

import argparse
from pathlib import Path
import subprocess
import sys

# 添加scripts目录到Python路径
current_dir = Path(__file__).resolve().parent
script_dir = current_dir / 'scripts'
sys.path.insert(0, str(script_dir))

from scripts.config_manager import Config
from scripts.blog_processor import BlogProcessor

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

def main():
    config = Config()
    
    parser = argparse.ArgumentParser(description='将Markdown文件发布到Hugo博客')
    parser.add_argument('--source', 
                       default=config.get('paths.obsidian.vault'),
                       help='包含markdown文件的源目录')
    parser.add_argument('--hugo-dir',
                       default=config.get('paths.hugo.blog'),
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
    
    # 创建博客处理器实例
    processor = BlogProcessor(source_dir, hugo_dir)
    
    # 根据参数执行相应操作
    if args.preview:
        processor.preview_site()
    elif args.republish:
        # 重新发布流程
        print_header("开始重新发布所有文章")
        published = processor.list_published_markdowns()
        if not published:
            print_warning("没有已发布的文章")
            return
            
        print_step(1, "取消所有文章的发布")
        for md_file, _ in published:
            article_name = Path(md_file).stem
            if processor.unpublish_article(article_name):
                print_success(f"已取消发布: {article_name}")
                
        print_step(2, "重新发布所有文章")
        processed_files = processor.process_markdown_files(as_draft=args.draft)
        
        if not processed_files:
            print_warning("没有处理任何文件")
            return
            
        print_success(f"成功处理了 {len(processed_files)} 个文件")
        
        print_step(3, "部署到远程仓库")
        commit_msg = "重新发布所有文章"
        repo_source = config.get('repositories.source.url')
        repo_pages = config.get('repositories.pages.url')
        if processor.deploy_to_repos(repo_source, repo_pages, commit_msg):
            print_success("所有文章已重新发布并部署")
        return
    elif args.unpublish:
        # 取消发布流程
        published = processor.list_published_markdowns()
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
            processor.set_publish_false(md_file)
            article_name = Path(md_file).stem
            processor.unpublish_article(article_name)
        
        print(f"{COLOR_YELLOW}推送到远端...{COLOR_RESET}")
        commit_msg = input(f"请输入取消发布的提交信息: ").strip() or "Unpublish articles"
        repo_source = config.get('repositories.source.url')
        repo_pages = config.get('repositories.pages.url')
        processor.deploy_to_repos(repo_source, repo_pages, commit_msg)
        return
    else:
        # 正常发布流程
        # 处理文件
        processed_files = processor.process_markdown_files(args.files, as_draft=args.draft)
        
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
            
            repo_source = config.get('repositories.source.url')
            repo_pages = config.get('repositories.pages.url')
            processor.deploy_to_repos(repo_source, repo_pages, commit_msg)

if __name__ == '__main__':
    main()
