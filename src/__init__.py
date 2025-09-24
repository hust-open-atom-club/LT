"""
初始化模块
"""

from .translation_agent import TranslationAgent
from .markdown_parser import MarkdownParser, Metadata
from .translator import SmartTranslator
from .text_chunker import MarkdownChunker, TextChunk
from .summary_generator import SummaryGenerator

__version__ = "1.0.0"
__author__ = "Translation Agent Developer"

__all__ = [
    "TranslationAgent",
    "MarkdownParser",
    "Metadata",
    "SmartTranslator",
    "MarkdownChunker",
    "TextChunk",
    "SummaryGenerator"
]