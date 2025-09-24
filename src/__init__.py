"""
智能翻译代理

目录结构:
- utils/: 工具和基础设施层 (配置管理、LLM工厂等)
- core/: 核心业务逻辑层 (翻译器、文本处理等)
"""

# 导入工具层
from .utils import ConfigManager, config_manager, LLMFactory

# 导入核心业务层
from .core import (
    TranslationAgent,
    MarkdownParser, 
    Metadata,
    SmartTranslator,
    MarkdownChunker,
    TextChunk,
    SummaryGenerator
)

__version__ = "1.0.0"
__author__ = "MU-ty"

__all__ = [
    "ConfigManager",
    "config_manager", 
    "LLMFactory",
    "TranslationAgent",
    "MarkdownParser",
    "Metadata",
    "SmartTranslator",
    "MarkdownChunker",
    "TextChunk",
    "SummaryGenerator"
]