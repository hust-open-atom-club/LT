"""
reStructuredText (RST) 文档处理器
"""

import re
from typing import List, Dict, Tuple, Optional
from .document_processor import DocumentProcessor, DocumentBlock


class RSTProcessor(DocumentProcessor):
    """RST 文档处理器"""
    
    # RST 标题字符
    TITLE_CHARS = '=-~`:\'"^_*+#<>'
    
    # RST 指令模式
    DIRECTIVE_PATTERN = re.compile(r'^\.\.\s+\w+::')
    
    # 代码块缩进模式
    CODE_INDENT_PATTERN = re.compile(r'^(\s{4,}|\t+)')
    
    def __init__(self):
        self.in_code_block = False
        self.in_directive_block = False
        self.directive_indent = 0
    
    def parse(self, content: str) -> List[DocumentBlock]:
        """解析 RST 文档为块"""
        blocks = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]

            # 检测 overline + title + underline 组合标题
            # Pattern: ========\nTitle Text\n========
            if (
                i + 2 < len(lines)
                and self._is_title_underline(lines[i])
                and not self._is_title_underline(lines[i + 1])
                and self._is_title_underline(lines[i + 2])
                and lines[i].strip()[0] == lines[i + 2].strip()[0]
            ):
                underline_char = lines[i].strip()[0]
                level = self._get_title_level(underline_char)
                # overline
                blocks.append(DocumentBlock(
                    type='title_overline',
                    content=lines[i],
                    translatable=False,
                    metadata={'level': level, 'char': underline_char}
                ))
                # title text
                blocks.append(DocumentBlock(
                    type='title',
                    content=lines[i + 1],
                    translatable=True,
                    metadata={'level': level, 'underline_char': underline_char, 'overline': True}
                ))
                # underline
                blocks.append(DocumentBlock(
                    type='title_underline',
                    content=lines[i + 2],
                    translatable=False,
                    metadata={'level': level, 'char': underline_char, 'overline': True}
                ))
                i += 3
                continue
            
            # 检测标题（下划线样式）
            if i + 1 < len(lines) and self._is_title_underline(lines[i + 1]):
                level = self._get_title_level(lines[i + 1][0])
                blocks.append(DocumentBlock(
                    type='title',
                    content=line,
                    translatable=True,
                    metadata={'level': level, 'underline_char': lines[i + 1][0]}
                ))
                # 记录下划线（不翻译）
                blocks.append(DocumentBlock(
                    type='title_underline',
                    content=lines[i + 1],
                    translatable=False,
                    metadata={'level': level}
                ))
                i += 2
                continue
            
            # 上下划线样式的标题
            if (i > 0 and i + 1 < len(lines) and 
                self._is_title_underline(lines[i - 1]) and 
                self._is_title_underline(lines[i + 1]) and
                lines[i - 1][0] == lines[i + 1][0]):
                # 这种情况在上一次循环已经处理了，跳过
                i += 1
                continue
            
            # .. directive::
            if self.DIRECTIVE_PATTERN.match(line.strip()):
                self.in_directive_block = True
                self.directive_indent = len(line) - len(line.lstrip())
                blocks.append(DocumentBlock(
                    type='directive',
                    content=line,
                    translatable=False
                ))
                i += 1
                continue
            
            # 缩进的内容
            if self.in_directive_block:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
                if line.strip() and current_indent > self.directive_indent:
                    blocks.append(DocumentBlock(
                        type='directive_content',
                        content=line,
                        translatable=False
                    ))
                    i += 1
                    continue
                else:
                    self.in_directive_block = False
            
            # 代码块（literal block :: 后的缩进内容）
            if i > 0 and lines[i - 1].rstrip().endswith('::'):
                if self.CODE_INDENT_PATTERN.match(line) or not line.strip():
                    if not self.in_code_block:
                        self.in_code_block = True
                    blocks.append(DocumentBlock(
                        type='code',
                        content=line,
                        translatable=False
                    ))
                    i += 1
                    continue
            
            # 代码块内容（持续缩进）
            if self.in_code_block:
                if self.CODE_INDENT_PATTERN.match(line) or not line.strip():
                    blocks.append(DocumentBlock(
                        type='code',
                        content=line,
                        translatable=False
                    ))
                    i += 1
                    continue
                else:
                    self.in_code_block = False
            
            # 检测表格分隔符
            if self._is_table_separator(line):
                blocks.append(DocumentBlock(
                    type='table_separator',
                    content=line,
                    translatable=False
                ))
                i += 1
                continue
            
            # 检测列表项
            list_match = re.match(r'^(\s*)([-*+]|\d+\.|\w+\))\s+(.+)$', line)
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
        """从块重构 RST 文档"""
        lines = []
        
        for i, block in enumerate(blocks):
            if block.type == 'title_overline': # overline 原样保留，后续 title_underline 会再输出
                lines.append(block.content)
                continue
            if block.type == 'title':
                lines.append(block.content)
                # 如果是 overline+underline 结构，直接保留后续 underline，不重新生成
                if i + 1 < len(blocks) and blocks[i + 1].type == 'title_underline':
                    underline_block = blocks[i + 1]
                    if block.metadata.get('overline'):
                        # 已存在 overline/underline，保持不变
                        lines.append(underline_block.content)
                        continue
                    else:
                        # 仅 underline 结构，重新计算长度
                        underline_char = block.metadata.get('underline_char', '=')
                        display_length = self._calculate_display_length(block.content)
                        lines.append(underline_char * display_length)
                        continue
            elif block.type == 'title_underline':
                # 如果上一个不是标题，说明需要单独处理
                if i == 0 or blocks[i - 1].type != 'title':
                    lines.append(block.content)
            elif block.type == 'list_item':
                # 保持列表项的格式
                lines.append(block.content)
            else:
                # 其他类型直接输出
                lines.append(block.content)
        
        return '\n'.join(lines)
    
    def get_translatable_content(self, blocks: List[DocumentBlock]) -> str:
        """提取所有可翻译的内容"""
        translatable_texts = []
        
        for block in blocks:
            if block.translatable and block.content.strip():
                # 对于列表项，只提取文本部分
                if block.type == 'list_item' and 'text' in block.metadata:
                    translatable_texts.append(block.metadata['text'])
                else:
                    translatable_texts.append(block.content.strip())
        
        return '\n'.join(translatable_texts)
    
    def extract_metadata(self, content: str) -> Tuple[Optional[Dict], str]:
        """
        RST 通常使用文档开头的字段列表作为元数据
        格式如: :Field: value
        """
        metadata = {}
        lines = content.split('\n')
        metadata_end = 0
        
        field_pattern = re.compile(r'^:(\w+):\s*(.+)$')
        
        for i, line in enumerate(lines):
            match = field_pattern.match(line.strip())
            if match:
                field_name, field_value = match.groups()
                metadata[field_name.lower()] = field_value.strip()
                metadata_end = i + 1
            elif line.strip() and not match:
                # 遇到非字段行，元数据结束
                break
        
        if metadata:
            content_without_metadata = '\n'.join(lines[metadata_end:])
            return metadata, content_without_metadata.lstrip()
        else:
            return None, content
    
    def format_with_metadata(self, metadata: Dict, content: str) -> str:
        """将元数据和内容格式化为完整的 RST 文档"""
        if not metadata:
            return content
        
        metadata_lines = []
        for key, value in metadata.items():
            # 首字母大写
            field_name = key.capitalize()
            metadata_lines.append(f":{field_name}: {value}")
        
        return '\n'.join(metadata_lines) + '\n\n' + content
    
    def _is_title_underline(self, line: str) -> bool:
        """检查是否为标题下划线"""
        if not line.strip():
            return False
        stripped = line.strip()
        if len(stripped) < 2:
            return False
        chars = set(stripped)
        return len(chars) == 1 and chars.pop() in self.TITLE_CHARS
    
    def _get_title_level(self, char: str) -> int:
        """根据字符获取标题级别"""
        levels = {
            '=': 1,  # 主标题
            '-': 2,  # 二级标题
            '~': 3,  # 三级标题
            '`': 4,  # 四级标题
            ':': 5,  # 五级标题
        }
        return levels.get(char, 6)
    
    def _is_table_separator(self, line: str) -> bool:
        """检查是否为表格分隔符"""
        stripped = line.strip()
        if not stripped:
            return False
        # 表格分隔符通常是 ===== 或 ----- 或组合
        return all(c in '=- +' for c in stripped) and any(c in '=-' for c in stripped)
    
    def _calculate_display_length(self, text: str) -> int:
        """
        计算文本的显示长度（中文字符算2个宽度，ASCII算1个）
        """
        length = 0
        for char in text:
            if ord(char) > 127:  # 非ASCII字符
                length += 2
            else:
                length += 1
        return length
