# src/core/prompt_manager.py
import os
import glob
from typing import Dict
from pathlib import Path

# 兼容性导入
try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    from langchain.prompts import ChatPromptTemplate


class PromptManager:
    """
    Prompt 管理器
    负责从文件系统中加载提示词模板，实现代码与数据的解耦。
    """

    def __init__(self, prompts_dir: str = None):
        # 如果未指定路径，默认使用当前文件同级目录下的 'prompts' 文件夹
        if prompts_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.prompts_dir = os.path.join("../..", current_dir, "prompts")
        else:
            self.prompts_dir = prompts_dir

        self._prompts: Dict[str, str] = {}
        self._load_prompts()

    def _load_prompts(self):
        """自动加载目录下所有的 .txt 文件作为 prompt"""
        if not os.path.exists(self.prompts_dir):
            # 这里可以选择报错，或者创建一个默认的 prompts 文件夹
            print(f"警告: Prompt 目录不存在: {self.prompts_dir}")
            return

        # 查找所有 txt 文件
        search_path = os.path.join(self.prompts_dir, "*.txt")
        files = glob.glob(search_path)

        for file_path in files:
            try:
                file_name = Path(file_path).stem  # 获取文件名（不含后缀），如 'kernel_rst'
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        self._prompts[file_name] = content
                        # print(f"已加载 Prompt 模板: {file_name}")
            except Exception as e:
                print(f"加载 Prompt 文件失败 {file_path}: {e}")

        # 检查是否为空，如果为空可能导致后续运行崩溃
        if not self._prompts:
            print("警告: 未加载到任何 Prompt 模板，请检查 prompts 文件夹。")

    def get_prompt(self, template_name: str) -> ChatPromptTemplate:
        """
        获取 LangChain 的 Prompt 模板对象
        Args:
            template_name: 模板名称（对应文件名，不含后缀），例如 'kernel_rst'
        """
        if template_name not in self._prompts:
            # 提供一个友好的错误提示，列出可用的模板
            available = ", ".join(self._prompts.keys())
            raise ValueError(f"未找到名为 '{template_name}' 的 Prompt 模板。当前可用: [{available}]")

        return ChatPromptTemplate.from_template(self._prompts[template_name])

    def reload(self):
        """重新加载所有 Prompt (用于调试，无需重启程序)"""
        self._prompts.clear()
        self._load_prompts()
