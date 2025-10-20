"""
核心业务逻辑层
"""

from .translator import SmartTranslator
from .translation_agent import TranslationAgent
from .markdown_parser import MarkdownParser, Metadata
from .text_chunker import MarkdownChunker, TextChunk
from .summary_generator import SummaryGenerator
from .universal_translator import UniversalTranslator
from .document_processor import DocumentProcessor, ProcessorFactory, DocumentBlock
from .markdown_document_processor import MarkdownDocumentProcessor
from .rst_processor import RSTProcessor

# 注册文档处理器
ProcessorFactory.register(['.md', '.markdown'], MarkdownDocumentProcessor)
ProcessorFactory.register(['.rst', '.rest'], RSTProcessor)

__all__ = [
    'SmartTranslator',
    'TranslationAgent', 
    'MarkdownParser',
    'Metadata',
    'MarkdownChunker',
    'TextChunk',
    'SummaryGenerator',
    'UniversalTranslator',
    'DocumentProcessor',
    'ProcessorFactory',
    'DocumentBlock',
    'MarkdownDocumentProcessor',
    'RSTProcessor'
]