import yaml
from pathlib import Path
from openai import OpenAI
import logging

class APIHandler:
    """处理API调用的类"""
    
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.client = self._init_client()
        self.prompt_template = self._load_prompt_template()
    
    def _load_config(self, config_path):
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        api_config = self.config['api']['deepseek']
        return OpenAI(
            api_key=api_config['api_key'],
            base_url=api_config['base_url']
        )
    
    def _load_prompt_template(self):
        """加载prompt模板"""
        prompt_path = Path('prompt.txt')
        if not prompt_path.exists():
            raise FileNotFoundError("prompt.txt文件不存在")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def generate_summary(self, content):
        """生成博客摘要"""
        try:
            # 准备prompt
            prompt = self.prompt_template.replace('{{content}}', content)
            
            # 调用API
            response = self.client.chat.completions.create(
                model=self.config['api']['deepseek']['model'],
                messages=[
                    {"role": "system", "content": "你是一个专业的博客摘要生成助手。"},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            # 获取摘要
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            logging.error(f"生成摘要时出错: {str(e)}")
            return None 