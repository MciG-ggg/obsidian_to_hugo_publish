import yaml
from pathlib import Path
from datetime import datetime

class FrontMatter:
    """博客文章头部信息管理类"""
    
    def __init__(self, yaml_data=None):
        """
        初始化头部信息
        :param yaml_data: YAML数据字典
        """
        self._data = yaml_data or {}
        self._normalize_fields()
    
    def _normalize_fields(self):
        """标准化字段格式"""
        # 处理tags字段
        tags = self._data.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        elif tags is None:
            tags = []
        self._data['tags'] = tags
        
        # 处理categories字段
        categories = self._data.get('categories', [])
        if isinstance(categories, str):
            categories = [categories]
        elif categories is None:
            categories = []
        self._data['categories'] = categories
        
        # 处理其他字段
        for key, value in self._data.items():
            if value is None:
                self._data[key] = ''
    
    @property
    def tags(self):
        """获取标签列表"""
        return self._data.get('tags', [])
    
    @property
    def categories(self):
        """获取分类列表"""
        return self._data.get('categories', [])
    
    @property
    def title(self):
        """获取标题"""
        return self._data.get('title', '')
    
    @property
    def date(self):
        """获取日期"""
        return self._data.get('date', '')
    
    @property
    def draft(self):
        """获取草稿状态"""
        return self._data.get('draft', False)
    
    @property
    def publish(self):
        """获取发布状态"""
        return self._data.get('publish', False)
    
    @property
    def description(self):
        """获取描述"""
        return self._data.get('description', '')
    
    @property
    def image(self):
        """获取图片"""
        return self._data.get('image', '')
    
    def to_dict(self):
        """转换为字典"""
        return self._data.copy()
    
    def update(self, data):
        """更新数据"""
        self._data.update(data)
        self._normalize_fields()
    
    def __str__(self):
        """字符串表示"""
        return str(self._data)

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
        return FrontMatter(yaml_data), parts[2]
    except yaml.YAMLError:
        return None, content

def load_tag_category_mapping():
    """加载标签到分类的映射关系"""
    mapping_file = Path(__file__).parent.parent / 'tag_category_mapping.yaml'
    if not mapping_file.exists():
        return {}
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"加载标签映射文件时出错: {str(e)}")
        return {}

def get_categories_from_tags(tags, tag_mapping):
    """根据标签获取对应的分类"""
    if not tags or not tag_mapping:
        return []
    
    categories = set()
    for tag in tags:
        if tag in tag_mapping:
            categories.add(tag_mapping[tag])
    
    return list(categories)

def update_tag_category_mapping(hugo_dir):
    """根据现有文章更新标签到分类的映射关系"""
    mapping_file = Path(__file__).parent.parent / 'tag_category_mapping.yaml'
    hugo_dir = Path(hugo_dir)
    
    # 收集所有文章中的标签和分类
    tag_category_pairs = {}
    for md_file in (hugo_dir / 'content' / 'post').rglob('*.md'):
        front_matter, _ = extract_yaml_and_content(md_file)
        if not front_matter:
            continue
        
        tags = front_matter.tags
        categories = front_matter.categories
        
        # 如果文章同时有标签和分类，记录它们的对应关系
        if tags and categories:
            for tag in tags:
                if tag not in tag_category_pairs:
                    tag_category_pairs[tag] = set()
                tag_category_pairs[tag].update(categories)
    
    # 加载现有的映射关系
    existing_mapping = {}
    if mapping_file.exists():
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                existing_mapping = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"加载现有映射文件时出错: {str(e)}")
    
    # 更新映射关系
    updated_mapping = {}
    
    # 1. 首先处理一对一的关系
    for tag, categories in tag_category_pairs.items():
        if len(categories) == 1:
            # 如果标签只对应一个分类，直接使用
            updated_mapping[tag] = list(categories)[0]
    
    # 2. 处理多对一的关系
    for tag, categories in tag_category_pairs.items():
        if len(categories) > 1:
            # 如果标签在现有映射中存在，保持原有映射
            if tag in existing_mapping:
                updated_mapping[tag] = existing_mapping[tag]
            else:
                # 如果标签对应多个分类，使用第一个分类
                print(f"标签 '{tag}' 对应多个分类: {categories}，使用第一个分类")
                updated_mapping[tag] = list(categories)[0]
    
    # 3. 保留现有映射中的其他标签
    for tag, category in existing_mapping.items():
        if tag not in updated_mapping:
            updated_mapping[tag] = category
    
    # 4. 验证映射关系
    for tag, category in updated_mapping.items():
        if tag in tag_category_pairs and category not in tag_category_pairs[tag]:
            print(f"警告: 标签 '{tag}' 的映射分类 '{category}' 不在其实际分类列表中")
    
    # 保存更新后的映射关系
    try:
        with open(mapping_file, 'w', encoding='utf-8') as f:
            f.write("# 标签到分类的映射关系\n")
            f.write("# 格式：\n")
            f.write("# tag_name: category_name\n")
            f.write("# 一个标签只能对应一个分类\n")
            f.write("# 一个分类可以对应多个标签\n\n")
            # 按字母顺序排序
            sorted_mapping = dict(sorted(updated_mapping.items(), key=lambda x: x[0].lower()))
            yaml.dump(sorted_mapping, f, allow_unicode=True, sort_keys=False)
        print(f"已更新标签映射文件: {mapping_file}")
    except Exception as e:
        print(f"保存标签映射文件时出错: {str(e)}") 