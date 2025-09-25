"""
文本分块
"""

import re
import tiktoken
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class TextChunk:
    """文本块结构"""
    content: str
    chunk_type: str  # 'heading', 'paragraph', 'list', 'code', 'quote'
    level: int = 0   # 标题级别（用于heading）
    start_pos: int = 0
    end_pos: int = 0


class MarkdownChunker:
    """Markdown分块"""
    
    def __init__(self, max_tokens: int = 1000, model: str = "gpt-3.5-turbo"):

        self.max_tokens = max_tokens
        self.encoding = self._get_encoding(model)
        
        # 编译正则表达式模式
        self.patterns = {
            'heading': re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
            'code_block': re.compile(r'```[\s\S]*?```', re.MULTILINE),
            'list_item': re.compile(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', re.MULTILINE),
            'quote': re.compile(r'^>\s+(.+)$', re.MULTILINE),
            'paragraph': re.compile(r'^(.+)$', re.MULTILINE)
        }
    
    def _get_encoding(self, model: str):

        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            if model.lower().startswith('qwen'):
                # Qwen模型使用cl100k_base编码器
                return tiktoken.get_encoding("cl100k_base")
            elif model.lower().startswith('gpt-4'):
                return tiktoken.get_encoding("cl100k_base")
            elif model.lower().startswith('gpt-3.5'):
                return tiktoken.get_encoding("cl100k_base")
            else:
                # 默认cl100k_base
                return tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """计算文本的token数量"""
        return len(self.encoding.encode(text))
    
    def split_by_structure(self, content: str) -> List[TextChunk]:

        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_type = None
        current_level = 0
        start_pos = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped_line = line.strip()
            
            if stripped_line.startswith('```'): #代码
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk)
                    chunks.append(TextChunk(
                        content=chunk_content,
                        chunk_type=current_type or 'paragraph',
                        level=current_level,
                        start_pos=start_pos,
                        end_pos=start_pos + len(chunk_content)
                    ))
                    current_chunk = []

                code_lines = [line]
                i += 1
                while i < len(lines):
                    code_lines.append(lines[i])
                    if lines[i].strip().startswith('```'):
                        break
                    i += 1
                
                code_content = '\n'.join(code_lines)
                chunks.append(TextChunk(
                    content=code_content,
                    chunk_type='code',
                    start_pos=start_pos,
                    end_pos=start_pos + len(code_content)
                ))
                start_pos += len(code_content) + 1
                current_type = None
                current_level = 0
                i += 1
                continue
            
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk)
                    chunks.append(TextChunk(
                        content=chunk_content,
                        chunk_type=current_type or 'paragraph',
                        level=current_level,
                        start_pos=start_pos,
                        end_pos=start_pos + len(chunk_content)
                    ))
                    current_chunk = []
                
                level = len(heading_match.group(1))
                current_chunk = [line]
                current_type = 'heading'
                current_level = level
                start_pos = sum(len(chunk.content) + 1 for chunk in chunks)
                i += 1
                continue

            list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', line)
            if list_match:
                if current_type != 'list':
                    if current_chunk:
                        chunk_content = '\n'.join(current_chunk)
                        chunks.append(TextChunk(
                            content=chunk_content,
                            chunk_type=current_type or 'paragraph',
                            level=current_level,
                            start_pos=start_pos,
                            end_pos=start_pos + len(chunk_content)
                        ))
                        current_chunk = []
                    
                    current_type = 'list'
                    current_level = 0
                    start_pos = sum(len(chunk.content) + 1 for chunk in chunks)
                
                current_chunk.append(line)
                i += 1
                continue

            if line.startswith('>'):
                if current_type != 'quote':
                    if current_chunk:
                        chunk_content = '\n'.join(current_chunk)
                        chunks.append(TextChunk(
                            content=chunk_content,
                            chunk_type=current_type or 'paragraph',
                            level=current_level,
                            start_pos=start_pos,
                            end_pos=start_pos + len(chunk_content)
                        ))
                        current_chunk = []
                    
                    current_type = 'quote'
                    current_level = 0
                    start_pos = sum(len(chunk.content) + 1 for chunk in chunks)
                
                current_chunk.append(line)
                i += 1
                continue
            
            if not stripped_line:
                if current_chunk:
                    current_chunk.append(line)
                i += 1
                continue
            
            if current_type != 'paragraph':
                
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk)
                    chunks.append(TextChunk(
                        content=chunk_content,
                        chunk_type=current_type or 'paragraph',
                        level=current_level,
                        start_pos=start_pos,
                        end_pos=start_pos + len(chunk_content)
                    ))
                    current_chunk = []
                
                current_type = 'paragraph'
                current_level = 0
                start_pos = sum(len(chunk.content) + 1 for chunk in chunks)
            
            current_chunk.append(line)
            i += 1
        
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            chunks.append(TextChunk(
                content=chunk_content,
                chunk_type=current_type or 'paragraph',
                level=current_level,
                start_pos=start_pos,
                end_pos=start_pos + len(chunk_content)
            ))
        
        return chunks
    
    def merge_small_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        合并小文本块
        """
        merged_chunks = []
        current_merged = None
        
        for chunk in chunks:
            chunk_tokens = self.count_tokens(chunk.content)
            
            if chunk_tokens > self.max_tokens:
                if current_merged:
                    merged_chunks.append(current_merged)
                    current_merged = None

                split_chunks = self._split_large_chunk(chunk)
                merged_chunks.extend(split_chunks)
                continue

            if current_merged is None:
                current_merged = TextChunk(
                    content=chunk.content,
                    chunk_type=chunk.chunk_type,
                    level=chunk.level,
                    start_pos=chunk.start_pos,
                    end_pos=chunk.end_pos
                )
                continue

            merged_content = current_merged.content + '\n\n' + chunk.content
            merged_tokens = self.count_tokens(merged_content)
            
            if merged_tokens <= self.max_tokens:

                current_merged.content = merged_content
                current_merged.end_pos = chunk.end_pos
            else:

                merged_chunks.append(current_merged)
                current_merged = TextChunk(
                    content=chunk.content,
                    chunk_type=chunk.chunk_type,
                    level=chunk.level,
                    start_pos=chunk.start_pos,
                    end_pos=chunk.end_pos
                )
        
        if current_merged:
            merged_chunks.append(current_merged)
        
        return merged_chunks
    
    def _split_large_chunk(self, chunk: TextChunk) -> List[TextChunk]:
        """
        分割大文本块
        """
        if chunk.chunk_type == 'code':
            # 代码块不分
            return [chunk]
        
        sentences = re.split(r'(?<=[.!?])\s+', chunk.content)
        split_chunks = []
        current_content = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.max_tokens and current_content:
                # 生成新块
                split_chunks.append(TextChunk(
                    content=' '.join(current_content),
                    chunk_type=chunk.chunk_type,
                    level=chunk.level
                ))
                current_content = [sentence]
                current_tokens = sentence_tokens
            else:
                current_content.append(sentence)
                current_tokens += sentence_tokens
        
        if current_content:
            split_chunks.append(TextChunk(
                content=' '.join(current_content),
                chunk_type=chunk.chunk_type,
                level=chunk.level
            ))
        
        return split_chunks if split_chunks else [chunk]
    
    def chunk_text(self, content: str) -> List[TextChunk]:
        """
        主要的分块方法
        """
        # 按结构分块
        structural_chunks = self.split_by_structure(content)
        # 合并小块
        optimized_chunks = self.merge_small_chunks(structural_chunks)
        
        return optimized_chunks