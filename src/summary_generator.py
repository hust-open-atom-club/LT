"""
摘要生成器
使用LangChain实现文本摘要功能
"""

from typing import List
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseOutputParser
from langchain.schema.runnable import RunnablePassthrough
import os
from .text_chunker import TextChunk
from .llm_factory import LLMFactory


class SummaryOutputParser(BaseOutputParser):
    
    def parse(self, text: str) -> str:
        return text.strip()


class SummaryGenerator:
    """摘要生成器"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.2, provider: str = None,
                 openai_api_key: str = None, openai_base_url: str = None, qwen_api_key: str = None):

        self.llm = LLMFactory.create_llm(
            model_name=model_name,
            provider=provider,
            temperature=temperature,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            qwen_api_key=qwen_api_key
        )
        
        # 原文摘要prompt
        self.original_summary_template = ChatPromptTemplate.from_template(
            """你是一个专业的文档分析师。请为以下英文文档生成一个详细的中文摘要。

要求：
1. 摘要应该涵盖文档的主要观点、关键信息和结构
2. 保持原文的逻辑顺序和层次结构
3. 使用简洁清晰的中文表达
4. 摘要长度应该是原文的20-30%
5. 确保包含所有重要的概念和细节

文档内容：
{content}

请生成详细的中文摘要："""
        )
        
        # 译文摘要prompt
        self.translated_summary_template = ChatPromptTemplate.from_template(
            """你是一个专业的文档分析师。请为以下中文译文生成一个详细的摘要。

要求：
1. 摘要应该涵盖译文的主要观点、关键信息和结构
2. 保持译文的逻辑顺序和层次结构
3. 使用简洁清晰的中文表达
4. 摘要长度应该是译文的20-30%
5. 确保包含所有重要的概念和细节

译文内容：
{content}

请生成详细的中文摘要："""
        )
        
        # 内容比较prompt
        self.comparison_template = ChatPromptTemplate.from_template(
            """你是一个专业的翻译质量检查员。请比较原文摘要和译文摘要，找出可能遗漏的内容。

原文摘要：
{original_summary}

译文摘要：
{translated_summary}

请分析：
1. 译文摘要是否完整覆盖了原文摘要的所有要点
2. 是否有遗漏的关键信息、概念或细节
3. 如果有遗漏，请具体列出缺失的内容

分析结果：
- 完整性评分：[1-10分，10分表示完全一致]
- 遗漏内容：[如果有遗漏，请列出具体内容；如果没有遗漏，请写"无"]
- 建议：[对翻译改进的具体建议]

请严格按照上述格式输出："""
        )
        
        # 创建处理链
        self.original_summary_chain = (
            self.original_summary_template 
            | self.llm 
            | SummaryOutputParser()
        )
        
        self.translated_summary_chain = (
            self.translated_summary_template 
            | self.llm 
            | SummaryOutputParser()
        )
        
        self.comparison_chain = (
            self.comparison_template 
            | self.llm 
            | SummaryOutputParser()
        )
    
    def generate_original_summary(self, content: str) -> str:
        """
        生成原文摘要
        
        Args:
            content: 英文原文内容
            
        Returns:
            中文摘要
        """
        try:
            summary = self.original_summary_chain.invoke({
                "content": content
            })
            return summary
        except Exception as e:
            print(f"生成原文摘要时出错: {e}")
            return f"摘要生成失败: {str(e)}"
    
    def generate_translated_summary(self, content: str) -> str:
        """
        生成译文摘要
        
        Args:
            content: 中文译文内容
            
        Returns:
            中文摘要
        """
        try:
            summary = self.translated_summary_chain.invoke({
                "content": content
            })
            return summary
        except Exception as e:
            print(f"生成译文摘要时出错: {e}")
            return f"摘要生成失败: {str(e)}"
    
    def compare_summaries(self, original_summary: str, translated_summary: str) -> dict:
        """
        比较原文摘要和译文摘要，找出遗漏内容
        
        Args:
            original_summary: 原文摘要
            translated_summary: 译文摘要
            
        Returns:
            包含比较结果的字典
        """
        try:
            comparison_result = self.comparison_chain.invoke({
                "original_summary": original_summary,
                "translated_summary": translated_summary
            })
            
            # 解析比较结果
            lines = comparison_result.split('\n')
            result = {
                "completeness_score": 0,
                "missing_content": "",
                "suggestions": "",
                "raw_result": comparison_result
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith("- 完整性评分："):
                    try:
                        # 提取分数
                        score_part = line.split("：")[1]
                        score = int(''.join(filter(str.isdigit, score_part)))
                        result["completeness_score"] = score
                    except:
                        pass
                elif line.startswith("- 遗漏内容："):
                    result["missing_content"] = line.split("：", 1)[1] if "：" in line else ""
                elif line.startswith("- 建议："):
                    result["suggestions"] = line.split("：", 1)[1] if "：" in line else ""
            
            return result
            
        except Exception as e:
            print(f"比较摘要时出错: {e}")
            return {
                "completeness_score": 0,
                "missing_content": f"比较失败: {str(e)}",
                "suggestions": "",
                "raw_result": f"比较失败: {str(e)}"
            }
    
    def generate_chunk_summaries(self, chunks: List[TextChunk]) -> List[str]:

        summaries = []
        
        for i, chunk in enumerate(chunks):
            print(f"正在生成第 {i+1}/{len(chunks)} 个块的摘要...")
            
            if chunk.chunk_type == 'code':
                summary = f"代码块：{chunk.content[:100]}..." if len(chunk.content) > 100 else f"代码块：{chunk.content}"
            else:
                summary = self.generate_original_summary(chunk.content)
            
            summaries.append(summary)
        
        return summaries