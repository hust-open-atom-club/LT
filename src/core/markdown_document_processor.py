"""
Markdown 文档处理器（基于新架构）
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import asdict
from .document_processor import DocumentProcessor, DocumentBlock
from .markdown_parser import MarkdownParser, Metadata


class MarkdownDocumentProcessor(DocumentProcessor):
    """Markdown 文档处理器"""
    
    # Markdown 语法模式
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$')
    CODE_FENCE_PATTERN = re.compile(r'^```(\w*)$')
    LIST_PATTERN = re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.+)$')
    BLOCKQUOTE_PATTERN = re.compile(r'^>\s*(.*)$')
    HORIZONTAL_RULE_PATTERN = re.compile(r'^(\*{3,}|-{3,}|_{3,})$')
    
    def __init__(self):
        self.in_code_block = False
        self.code_language = None
        # 统一复用 MarkdownParser 处理 front matter，避免重复实现
        self._metadata_parser = MarkdownParser()
    
    def parse(self, content: str) -> List[DocumentBlock]:
        """解析 Markdown 文档为块"""
        blocks = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检测代码围栏
            fence_match = self.CODE_FENCE_PATTERN.match(line.strip())
            if fence_match:
                if not self.in_code_block:
                    # 开始代码块
                    self.in_code_block = True
                    self.code_language = fence_match.group(1)
                    blocks.append(DocumentBlock(
                        type='code_fence_start',
                        content=line,
                        translatable=False,
                        metadata={'language': self.code_language}
                    ))
                else:
                    # 结束代码块
                    self.in_code_block = False
                    blocks.append(DocumentBlock(
                        type='code_fence_end',
                        content=line,
                        translatable=False
                    ))
                    self.code_language = None
                i += 1
                continue
            
            # 代码块内容
            if self.in_code_block:
                blocks.append(DocumentBlock(
                    type='code',
                    content=line,
                    translatable=False
                ))
                i += 1
                continue
            
            # 检测标题
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                hashes, title = heading_match.groups()
                level = len(hashes)
                blocks.append(DocumentBlock(
                    type='heading',
                    content=line,
                    translatable=True,
                    metadata={'level': level, 'hashes': hashes, 'title': title}
                ))
                i += 1
                continue
            
            # 检测水平分隔线
            if self.HORIZONTAL_RULE_PATTERN.match(line.strip()):
                blocks.append(DocumentBlock(
                    type='horizontal_rule',
                    content=line,
                    translatable=False
                ))
                i += 1
                continue
            
            # 检测列表项
            list_match = self.LIST_PATTERN.match(line)
            if list_match:
                indent, marker, text = list_match.groups()
                blocks.append(DocumentBlock(
                    type='list_item',
                    content=line,
                    translatable=True,
                    metadata={'indent': len(indent), 'marker': marker, 'text': text}
                ))
                i += 1
                continue
            
            # 检测引用块
            quote_match = self.BLOCKQUOTE_PATTERN.match(line)
            if quote_match:
                text = quote_match.group(1)
                blocks.append(DocumentBlock(
                    type='blockquote',
                    content=line,
                    translatable=True,
                    metadata={'text': text}
                ))
                i += 1
                continue
            
            # 空行
            if not line.strip():
                blocks.append(DocumentBlock(
                    type='blank',
                    content=line,
                    translatable=False
                ))
                i += 1
                continue
            
            # 普通段落
            blocks.append(DocumentBlock(
                type='paragraph',
                content=line,
                translatable=True
            ))
            i += 1
        
        return blocks
    
    def reconstruct(self, blocks: List[DocumentBlock]) -> str:
        """从块重构 Markdown 文档"""
        lines = []
        
        for block in blocks:
            if block.type == 'heading' and 'hashes' in block.metadata and 'title' in block.metadata:
                # 重新构建标题（保持原有的#数量）
                # 从翻译后的内容中提取标题文本
                content = block.content
                # 如果内容包含 #，提取出来
                if content.startswith('#'):
                    lines.append(content)
                else:
                    # 否则用原有的 # 加上新内容
                    lines.append(f"{block.metadata['hashes']} {content}")
            else:
                lines.append(block.content)
        
        return '\n'.join(lines)
    
    def get_translatable_content(self, blocks: List[DocumentBlock]) -> str:
        """提取所有可翻译的内容"""
        translatable_texts = []
        
        for block in blocks:
            if block.translatable and block.content.strip():
                # 对于标题，提取标题文本
                if block.type == 'heading' and 'title' in block.metadata:
                    translatable_texts.append(block.metadata['title'])
                # 对于列表项，提取文本部分
                elif block.type == 'list_item' and 'text' in block.metadata:
                    translatable_texts.append(block.metadata['text'])
                # 对于引用，提取文本部分
                elif block.type == 'blockquote' and 'text' in block.metadata:
                    translatable_texts.append(block.metadata['text'])
                else:
                    translatable_texts.append(block.content.strip())
        
        return '\n'.join(translatable_texts)
    
    def extract_metadata(self, content: str) -> Tuple[Optional[Dict], str]:
        """提取 YAML front matter，委托给 MarkdownParser。
        保持与旧接口一致：
        - 若原文没有 front matter -> 返回 (None, 原内容)
        - 若存在 -> 返回 (dict, 去除 front matter 的正文)
        """
        stripped = content.strip()
        match = self._metadata_parser.metadata_pattern.match(stripped)
        if not match:
            return None, content
        metadata_obj, body = self._metadata_parser.parse_text(stripped)
        return asdict(metadata_obj), body
    
    def format_with_metadata(self, metadata: Dict, content: str) -> str:
        """将元数据与正文重新组合。
        传入的是 dict（上层修改过），需转回 Metadata dataclass 以复用统一格式化逻辑。
        若 metadata 为空或 None，则直接返回正文，避免平白添加默认 front matter。
        """
        if not metadata:
            return content
        # 构造 Metadata 对象（未知字段忽略）
        meta_obj = Metadata()
        for k, v in metadata.items():
            if hasattr(meta_obj, k):
                setattr(meta_obj, k, v)
        return self._metadata_parser.format_output(meta_obj, content)
