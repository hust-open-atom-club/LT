"""
文档处理器基类和工厂
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DocumentBlock:
    """文档块"""
    type: str  # title, paragraph, code, directive, blank, etc.
    content: str
    translatable: bool = True
    metadata: Optional[Dict] = None  # 额外的元数据（如标题级别、语言等）
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DocumentProcessor(ABC):
    """文档处理器基类"""
    
    @abstractmethod
    def parse(self, content: str) -> List[DocumentBlock]:
        """
        解析文档为可翻译块
        
        Args:
            content: 文档内容
            
        Returns:
            文档块列表
        """
        pass
    
    @abstractmethod
    def reconstruct(self, blocks: List[DocumentBlock]) -> str:
        """
        从文档块重构文档
        
        Args:
            blocks: 文档块列表
            
        Returns:
            重构后的文档内容
        """
        pass
    
    @abstractmethod
    def get_translatable_content(self, blocks: List[DocumentBlock]) -> str:
        """
        提取所有可翻译的内容
        
        Args:
            blocks: 文档块列表
            
        Returns:
            可翻译的纯文本内容
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, content: str) -> Tuple[Optional[Dict], str]:
        """
        提取文档元数据
        
        Args:
            content: 文档内容
            
        Returns:
            (元数据字典, 去除元数据后的内容)
        """
        pass
    
    @abstractmethod
    def format_with_metadata(self, metadata: Dict, content: str) -> str:
        """
        将元数据和内容格式化为完整文档
        
        Args:
            metadata: 元数据字典
            content: 文档内容
            
        Returns:
            完整的文档字符串
        """
        pass


class ProcessorFactory:
    """文档处理器工厂"""
    
    _processors = {}
    
    @classmethod
    def register(cls, extensions: List[str], processor_class):
        """
        注册处理器
        
        Args:
            extensions: 支持的文件扩展名列表（如 ['.md', '.markdown']）
            processor_class: 处理器类
        """
        for ext in extensions:
            ext_lower = ext.lower()
            if not ext_lower.startswith('.'):
                ext_lower = '.' + ext_lower
            cls._processors[ext_lower] = processor_class
    
    @classmethod
    def create(cls, file_extension: str) -> DocumentProcessor:
        """
        根据文件扩展名创建处理器
        
        Args:
            file_extension: 文件扩展名（如 '.md' 或 'md'）
            
        Returns:
            文档处理器实例
            
        Raises:
            ValueError: 不支持的文件格式
        """
        ext_lower = file_extension.lower()
        if not ext_lower.startswith('.'):
            ext_lower = '.' + ext_lower
        
        processor_class = cls._processors.get(ext_lower)
        if not processor_class:
            supported = ', '.join(cls._processors.keys())
            raise ValueError(
                f"不支持的文件格式: {file_extension}\n"
                f"支持的格式: {supported}"
            )
        
        return processor_class()
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """获取所有支持的文件扩展名"""
        return list(cls._processors.keys())
    
    @classmethod
    def is_supported(cls, file_extension: str) -> bool:
        """检查是否支持某个文件扩展名"""
        ext_lower = file_extension.lower()
        if not ext_lower.startswith('.'):
            ext_lower = '.' + ext_lower
        return ext_lower in cls._processors
