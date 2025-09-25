"""
Markdown解析器和元数据处理模块
"""

import re
from typing import Dict, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class Metadata:
    """元数据"""
    status: str = "translating"
    title: str = "FILL_THE_TITLE_HERE"
    author: str = "FILL_THE_AUTHOR_HERE"
    collector: str = "FILL_YOUR_GITHUB_ID_HERE"
    collected_date: str = ""
    translator: str = "FILL_YOUR_GITHUB_ID_HERE"
    translating_date: str = ""
    link: str = "FILL_THE_LINK_HERE"
    
    def __post_init__(self):
        if not self.collected_date:
            self.collected_date = datetime.now().strftime("%Y%m%d")
        if not self.translating_date:
            self.translating_date = datetime.now().strftime("%Y%m%d")


class MarkdownParser:
    """Markdown文件解析器"""
    
    def __init__(self):
        self.metadata_pattern = re.compile(
            r'^---\n(.*?)\n---', 
            re.MULTILINE | re.DOTALL
        )
    
    def parse_file(self, file_path: str) -> Tuple[Metadata, str]:

        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return self.parse_text(text)
    
    def parse_text(self, text: str) -> Tuple[Metadata, str]:

        metadata_match = self.metadata_pattern.match(text.strip())
        
        if metadata_match:
            metadata_str = metadata_match.group(1)
            content = text[metadata_match.end():].strip()
            metadata = self._parse_metadata(metadata_str)
        else:
            metadata = Metadata()
            content = text.strip()
        
        return metadata, content
    
    def _parse_metadata(self, metadata_str: str) -> Metadata:
        metadata_dict = {}
        
        for line in metadata_str.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                metadata_dict[key.strip()] = value.strip()
        
        metadata = Metadata()
        for key, value in metadata_dict.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        return metadata
    
    def format_output(self, metadata: Metadata, content: str) -> str:

        metadata_lines = []
        for key, value in asdict(metadata).items():
            metadata_lines.append(f"{key}: {value}")
        
        metadata_section = "---\n" + "\n".join(metadata_lines) + "\n---\n"
        
        return metadata_section + "\n" + content
    
    def update_translation_metadata(self, metadata: Metadata, translator_id: str) -> Metadata:

        metadata.status = "translated"
        metadata.translator = translator_id
        metadata.translating_date = datetime.now().strftime("%Y%m%d")
        
        return metadata