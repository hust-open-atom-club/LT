"""
翻译器
"""

from typing import List, Dict, Tuple
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseOutputParser
from tqdm import tqdm
import re
import os

from .text_chunker import TextChunk, MarkdownChunker
from .summary_generator import SummaryGenerator
from .markdown_parser import Metadata
from ..utils.llm_factory import LLMFactory


class TranslationOutputParser(BaseOutputParser):
    """翻译输出解析"""
    
    def parse(self, text) -> str:
        if hasattr(text, 'content'):
            return text.content.strip()
        elif hasattr(text, 'text'):
            return text.text.strip()
        else:
            return str(text).strip()


class SmartTranslator:
    """翻译"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.1, provider: str = None, 
                 openai_api_key: str = None, openai_base_url: str = None, qwen_api_key: str = None):

        # 使用LLM_factory创建模型实例
        self.llm = LLMFactory.create_llm(
            model_name=model_name,
            provider=provider,
            temperature=temperature,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            qwen_api_key=qwen_api_key
        )
        self.model_name = model_name
        
        self.chunker = MarkdownChunker(max_tokens=800, model=model_name)
        self.summary_generator = SummaryGenerator(
            model_name, temperature=0.2, provider=provider,
            openai_api_key=openai_api_key, openai_base_url=openai_base_url, qwen_api_key=qwen_api_key
        )
        
        # 翻译prompt模板
        self.translation_template = ChatPromptTemplate.from_template(
            """你是一个专业的英译汉翻译专家，具有深厚的语言功底和跨文化理解能力。

翻译要求：
1. 准确传达原文的含义和语调
2. 保持Markdown格式完全不变（标题、列表、代码块、链接等）
3. 使用地道的中文表达，符合中文阅读习惯
4. 保持专业术语的准确性和一致性
5. 对于代码、URL、专有名词等，保持原文不变
6. 确保翻译的流畅性和可读性

请翻译以下内容，只输出翻译结果，不要添加任何解释或说明：

{content}

翻译结果："""
        )
        
        # 重新翻译prompt模板（用于处理遗漏内容）
        self.retranslation_template = ChatPromptTemplate.from_template(
            """你是一个专业的英译汉翻译专家。现在需要你重新翻译以下内容，特别注意包含所有重要信息。

原文：
{original_text}

之前的翻译存在遗漏，缺少以下内容：
{missing_content}

请重新进行完整翻译，确保：
1. 包含所有原文信息，特别是上述缺失的内容
2. 保持Markdown格式完全不变
3. 使用地道的中文表达
4. 确保翻译的准确性和完整性

只输出翻译结果："""
        )
        
        # 创建处理链
        self.translation_chain = (
            self.translation_template 
            | self.llm 
            | TranslationOutputParser()
        )
        
        self.retranslation_chain = (
            self.retranslation_template 
            | self.llm 
            | TranslationOutputParser()
        )
    
    def translate_chunk(self, chunk: TextChunk) -> str:
        """
        翻译单个文本块
        """
        try:
            if chunk.chunk_type == 'code':
                # 代码块特殊处理 - 只翻译注释
                return self._translate_code_block(chunk.content)
            
            translation = self.translation_chain.invoke({
                "content": chunk.content
            })
            
            return translation
            
        except Exception as e:
            print(f"翻译文本块时出错: {e}")
            return f"翻译失败: {chunk.content}"
    
    def _translate_code_block(self, code_content: str) -> str:
        """
        翻译代码块，只翻译注释部分
        """
        lines = code_content.split('\n')
        translated_lines = []
        
        for line in lines:
            # 如果是注释行，进行翻译
            if line.strip().startswith('#') or line.strip().startswith('//'):
                try:
                    comment_translation = self.translation_chain.invoke({
                        "content": line.strip()
                    })
                    # 保持原有的缩进
                    indent = len(line) - len(line.lstrip())
                    translated_lines.append(' ' * indent + comment_translation)
                except:
                    translated_lines.append(line)
            else:
                translated_lines.append(line)
        
        return '\n'.join(translated_lines)
    
    def translate_content(self, content: str) -> Tuple[str, Dict]:
        """
        翻译完整内容
        """
        print("开始分析和翻译文档")

        print("生成原文摘要")
        original_summary = self.summary_generator.generate_original_summary(content)

        print("正在分割文本")
        chunks = self.chunker.chunk_text(content)
        print(f"文本已分割为 {len(chunks)} 个块")
        
        print("正在翻译各个文本块")
        translated_chunks = []
        
        for i, chunk in enumerate(tqdm(chunks, desc="翻译进度")):
            translated_content = self.translate_chunk(chunk)
            translated_chunks.append(translated_content)

        translated_content = self._merge_translated_chunks(translated_chunks)

        print("正在生成译文摘要")
        translated_summary = self.summary_generator.generate_translated_summary(translated_content)

        print("正在检查翻译完整性")
        comparison_result = self.summary_generator.compare_summaries(
            original_summary, translated_summary
        )
        
        # 修改重译条件：只要有遗漏内容或评分低于8分，就触发重译
        has_missing_content = (comparison_result["missing_content"] and 
                              comparison_result["missing_content"].strip() and 
                              comparison_result["missing_content"] != "无")
        
        if comparison_result["completeness_score"] < 8 or has_missing_content:
            print(f"检测到翻译需要改进，完整性评分: {comparison_result['completeness_score']}/10")
            if has_missing_content:
                print(f"遗漏内容: {comparison_result['missing_content']}")
            print("正在重新翻译")
            
            retranslated_content = self._retranslate_with_focus(
                content, comparison_result["missing_content"], 
                chunks=chunks, translated_chunks=translated_chunks
            )
            
            if retranslated_content:
                translated_content = retranslated_content

                translated_summary = self.summary_generator.generate_translated_summary(translated_content)
                
                comparison_result = self.summary_generator.compare_summaries(
                    original_summary, translated_summary
                )
                print(f"重新翻译后的完整性评分: {comparison_result['completeness_score']}/10")
        
        stats = {
            "original_summary": original_summary,
            "translated_summary": translated_summary,
            "comparison_result": comparison_result,
            "chunk_count": len(chunks),
            "completeness_score": comparison_result["completeness_score"]
        }
        
        return translated_content, stats
    
    def _merge_translated_chunks(self, translated_chunks: List[str]) -> str:
        """
        合并文本块
        """
        # 简单合并，用双换行分隔
        return '\n\n'.join(chunk.strip() for chunk in translated_chunks if chunk.strip())
    
    def _retranslate_with_focus(self, original_content: str, missing_content: str, 
                                chunks: List[TextChunk] = None, translated_chunks: List[str] = None) -> str:
        """
        定向重新翻译缺失内容：
        1) 在chunk列表中定位包含缺失内容的chunk
        2) 扩展上下文窗口（左右各1-2个chunk）
        3) 只对相关片段进行重新翻译
        4) 将重译结果替换回原译文中
        """
        try:
            # 如果没有提供chunks，重新分块
            if chunks is None:
                chunks = self.chunker.chunk_text(original_content)
            if translated_chunks is None:
                return None
                
            # 查找包含缺失内容的chunk索引
            relevant_indices = []
            missing_keywords = missing_content.split()[:5]  # 取前5个关键词
            
            for i, chunk in enumerate(chunks):
                # 检查是否包含缺失内容的关键词
                chunk_lower = chunk.content.lower()
                missing_lower = missing_content.lower()
                
                # 直接匹配或关键词匹配
                if (missing_lower in chunk_lower or 
                    any(keyword.lower() in chunk_lower for keyword in missing_keywords if len(keyword) > 2)):
                    relevant_indices.append(i)
            
            # 如果没有找到相关chunk，使用前几个chunk作为回退
            if not relevant_indices:
                print("未找到相关chunk，使用前3个chunk进行重译")
                relevant_indices = list(range(min(3, len(chunks))))
            
            # 扩展上下文窗口
            expanded_indices = set()
            context_window = 1  # 左右各1个chunk
            
            for idx in relevant_indices:
                start = max(0, idx - context_window)
                end = min(len(chunks), idx + context_window + 1)
                for i in range(start, end):
                    expanded_indices.add(i)
            
            expanded_indices = sorted(list(expanded_indices))
            
            # 提取需要重译的片段
            segments_to_retranslate = []
            for idx in expanded_indices:
                segments_to_retranslate.append({
                    'index': idx,
                    'content': chunks[idx].content
                })
            
            print(f"正在重新翻译 {len(segments_to_retranslate)} 个相关片段...")
            
            # 构建重译的prompt
            segments_text = "\n\n---片段分隔---\n\n".join(
                f"片段{i+1}:\n{seg['content']}" 
                for i, seg in enumerate(segments_to_retranslate)
            )
            
            retranslation_prompt = ChatPromptTemplate.from_template("""
你是专业的英译汉翻译专家。请重新翻译以下片段，特别注意包含这些缺失信息：{missing_content}

要求：
1. 保持Markdown格式不变
2. 确保包含所有重要信息
3. 使用地道的中文表达
4. 对每个片段分别翻译，用"---译文分隔---"分隔

原文片段：
{segments}

只输出翻译结果：
""")
            
            retranslation_chain = retranslation_prompt | self.llm | TranslationOutputParser()
            
            retranslated_text = retranslation_chain.invoke({
                "missing_content": missing_content,
                "segments": segments_text
            })
            
            retranslated_segments = retranslated_text.split("---译文分隔---")
            # 如果分割数量不匹配，尝试按段落分割
            if len(retranslated_segments) != len(segments_to_retranslate):
                retranslated_segments = [seg.strip() for seg in retranslated_text.split('\n\n') if seg.strip()]
            
            updated_chunks = translated_chunks.copy()
            for i, seg_info in enumerate(segments_to_retranslate):
                if i < len(retranslated_segments):
                    updated_chunks[seg_info['index']] = retranslated_segments[i].strip()

            return self._merge_translated_chunks(updated_chunks)
            
        except Exception as e:
            print(f"定向重译时出错: {e}")
            try:
                context_size = min(1000, len(original_content) // 4)  # 最多1/4内容作为上下文
                limited_content = original_content[:context_size]
                
                retranslated = self.retranslation_chain.invoke({
                    "original_text": limited_content,
                    "missing_content": missing_content
                })
                return retranslated
            except Exception as e2:
                print(f"回退重译也失败: {e2}")
                return None
    
    def translate_with_context(self, content: str, context: str = "") -> str:
        """
        带上下文的翻译
        """
        if context:
            enhanced_prompt = ChatPromptTemplate.from_template(
                """你是一个专业的英译汉翻译专家。

上下文信息：
{context}

请翻译以下内容，考虑上下文的连贯性：

{content}

翻译结果："""
            )
            
            enhanced_chain = enhanced_prompt | self.llm | TranslationOutputParser()
            
            try:
                return enhanced_chain.invoke({
                    "content": content,
                    "context": context
                })
            except Exception as e:
                print(f"带上下文翻译时出错: {e}")
                return self.translate_chunk(TextChunk(content, 'paragraph'))
        else:
            return self.translate_chunk(TextChunk(content, 'paragraph'))