"""
通用文档翻译器
"""

import os
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import json

from .document_processor import ProcessorFactory, DocumentProcessor, DocumentBlock
from .translator import SmartTranslator
from .markdown_parser import Metadata
from langchain.prompts import ChatPromptTemplate
from .translator import TranslationOutputParser
from .text_chunker import TextChunk
from datetime import datetime
import re as _re

class UniversalTranslator:
    """通用文档翻译器 - 支持多种文档格式"""
    
    def __init__(self,
                 model_name: str = "gpt-3.5-turbo",
                 translator_id: str = "FILL_YOUR_GITHUB_ID_HERE",
                 max_tokens: int = 800,
                 provider: str = None,
                 openai_api_key: str = None,
                 openai_base_url: str = None,
                 qwen_api_key: str = None,
                 refine_threshold: int = 8,
                 enable_refine: bool = True):
        """初始化通用翻译器
        Args:
            model_name: 模型名称
            translator_id: 翻译者ID
            max_tokens: 最大token数（目前保留向后兼容，未直接使用）
            provider: LLM 提供商（可留空自动推断）
            openai_api_key: OpenAI API 密钥
            openai_base_url: OpenAI 基础 URL
            qwen_api_key: 通义千问 API 密钥
            refine_threshold: 触发重译的完整性评分阈值（0-10）
            enable_refine: 是否启用缺失内容自动改进流程
        """
        self.translator_id = translator_id
        self.model_name = model_name
        self.refine_threshold = refine_threshold
        self.enable_refine = enable_refine
        if provider in (None, '', 'auto'):
            guessed = None
            lower_model = model_name.lower()
            if 'gpt' in lower_model:
                guessed = 'openai'
            elif 'qwen' in lower_model:
                guessed = 'qwen'
            self.provider = guessed or 'openai'
        else:
            self.provider = provider

        self.translator = SmartTranslator(
            model_name=model_name,
            provider=self.provider,
            temperature=0.1,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            qwen_api_key=qwen_api_key
        )
    
    def translate_file(self,
                      input_file: str,
                      output_file: Optional[str] = None,
                      save_stats: bool = True) -> Dict:
        """
        翻译文件（自动识别格式）
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径（可选）
            save_stats: 是否保存统计信息
            
        Returns:
            翻译统计信息
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"输入文件不存在: {input_file}")
        
        # 获取文件扩展名
        file_path = Path(input_file)
        file_ext = file_path.suffix
        
        # 检查是否支持该格式
        if not ProcessorFactory.is_supported(file_ext):
            supported = ', '.join(ProcessorFactory.get_supported_extensions())
            raise ValueError(
                f"不支持的文件格式: {file_ext}\n"
                f"支持的格式: {supported}"
            )
        
        print(f"正在处理文件: {input_file}")
        print(f"文件格式: {file_ext}")

        processor = ProcessorFactory.create(file_ext)
        
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        metadata_dict, content_without_metadata = processor.extract_metadata(content)
        
        print(f"文档长度: {len(content_without_metadata)} 字符")
        if metadata_dict:
            print(f"检测到元数据: {list(metadata_dict.keys())}")

        blocks = processor.parse(content_without_metadata)
        print(f"文档已解析为 {len(blocks)} 个块")

        translatable_count = sum(1 for b in blocks if b.translatable)
        print(f"可翻译块: {translatable_count}/{len(blocks)}")
        
        # 针对 RST 采用逐块翻译，避免整篇合并造成结构破坏
        if file_ext in ['.rst']:
            print("使用逐块翻译模式 (RST)")
            translated_blocks, stats = self._translate_blocks_individually(blocks)
        else:
            # 提取可翻译内容 (md等)
            translatable_content = processor.get_translatable_content(blocks)
            # 翻译内容
            print("开始翻译...")
            translated_content, stats = self.translator.translate_content(translatable_content)
            # 更新块中的翻译内容
            translated_blocks = self._update_blocks_with_translation(
                blocks, translated_content, processor
            )
        
        # 重构文档
        reconstructed_content = processor.reconstruct(translated_blocks)
        
        # 更新元数据
        if metadata_dict:
            metadata_dict = self._update_metadata(metadata_dict)
            final_output = processor.format_with_metadata(metadata_dict, reconstructed_content)
        else:
            final_output = reconstructed_content
        
        # 添加翻译署名
        final_output = self._append_translation_signature(final_output, file_ext)
        
        if output_file is None:
            output_file = str(file_path.parent / f"{file_path.stem}_translated{file_ext}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_output)
        
        print(f"翻译完成，输出文件: {output_file}")
        
        # 统计信息
        if save_stats:
            stats_file = str(Path(output_file).with_suffix('.stats.json'))
            self._save_translation_stats(stats, stats_file)

        stats.update({
            "input_file": input_file,
            "output_file": output_file,
            "translator_id": self.translator_id,
            "file_format": file_ext,
            "total_blocks": len(blocks),
            "translatable_blocks": translatable_count
        })
        
        return stats

    def _translate_blocks_individually(self, blocks: List[DocumentBlock]) -> Tuple[List[DocumentBlock], Dict]:
        """逐块翻译（RST 专用）
        - 保持每个块的独立性
        - 避免整体拼接导致的格式错乱
        - 代码/指令/表格分隔/空行不翻译
        """
        translated_blocks: List[DocumentBlock] = []
        original_texts = []
        translated_texts = []
        
        for block in blocks:
            if block.translatable and block.content.strip():
                try:
                    result = self.translator.translate_chunk(
                        TextChunk(block.content, 'paragraph')
                    )
                except Exception:
                    result = block.content
                new_block = DocumentBlock(
                    type=block.type,
                    content=result,
                    translatable=True,
                    metadata=block.metadata.copy() if block.metadata else {}
                )
                original_texts.append(block.content)
                translated_texts.append(result)
            else:
                new_block = block
            translated_blocks.append(new_block)
        
        # 构造简单的统计信息（复用 summary/compare 能力）
        original_joined = '\n'.join(original_texts)
        translated_joined = '\n'.join(translated_texts)
        original_summary = self.translator.summary_generator.generate_original_summary(original_joined)
        translated_summary = self.translator.summary_generator.generate_translated_summary(translated_joined)
        comparison_result = self.translator.summary_generator.compare_summaries(
            original_summary, translated_summary
        )
        stats = {
            "original_summary": original_summary,
            "translated_summary": translated_summary,
            "comparison_result": comparison_result,
            "chunk_count": len(translated_texts),
            "completeness_score": comparison_result.get("completeness_score", 0)
        }
        # 重译判定逻辑
        missing_content = comparison_result.get("missing_content")
        has_missing = bool(missing_content and missing_content.strip() and missing_content.strip() != '无')
        if self.enable_refine and (comparison_result.get("completeness_score", 0) < self.refine_threshold or has_missing):
            print(f"检测到需要改进: 完整性评分 {comparison_result.get('completeness_score', 0)}/10")
            if has_missing:
                print(f"缺失内容描述: {missing_content}")
            improved_blocks = self._attempt_retranslation_rst(
                blocks, translated_blocks, missing_content or ""
            )
            if improved_blocks:
                translated_blocks = improved_blocks
                # 重新生成统计
                improved_original_texts = [b.content for b in blocks if b.translatable and b.content.strip()]
                improved_translated_texts = [b.content for b in translated_blocks if b.translatable and b.content.strip()]
                improved_original_joined = '\n'.join(improved_original_texts)
                improved_translated_joined = '\n'.join(improved_translated_texts)
                improved_original_summary = self.translator.summary_generator.generate_original_summary(improved_original_joined)
                improved_translated_summary = self.translator.summary_generator.generate_translated_summary(improved_translated_joined)
                improved_comp = self.translator.summary_generator.compare_summaries(
                    improved_original_summary, improved_translated_summary
                )
                stats.update({
                    "original_summary": improved_original_summary,
                    "translated_summary": improved_translated_summary,
                    "comparison_result": improved_comp,
                    "completeness_score": improved_comp.get("completeness_score", stats.get("completeness_score")),
                    "refine_mode": "targeted"
                })
                print(f"改进后完整性评分: {improved_comp.get('completeness_score')}/10")
            else:
                # 回退
                print("定向重译未成功或无改进，尝试整体重译补全关键信息……")
                full_blocks = self._full_retranslate_rst(blocks, translated_blocks, missing_content or "")
                if full_blocks:
                    translated_blocks = full_blocks
                    improved_original_texts = [b.content for b in blocks if b.translatable and b.content.strip()]
                    improved_translated_texts = [b.content for b in translated_blocks if b.translatable and b.content.strip()]
                    improved_original_joined = '\n'.join(improved_original_texts)
                    improved_translated_joined = '\n'.join(improved_translated_texts)
                    improved_original_summary = self.translator.summary_generator.generate_original_summary(improved_original_joined)
                    improved_translated_summary = self.translator.summary_generator.generate_translated_summary(improved_translated_joined)
                    improved_comp = self.translator.summary_generator.compare_summaries(
                        improved_original_summary, improved_translated_summary
                    )
                    stats.update({
                        "original_summary": improved_original_summary,
                        "translated_summary": improved_translated_summary,
                        "comparison_result": improved_comp,
                        "completeness_score": improved_comp.get("completeness_score", stats.get("completeness_score")),
                        "refine_mode": "full"
                    })
                    print(f"整体重译后完整性评分: {improved_comp.get('completeness_score')}/10")
        return translated_blocks, stats
    
    def _update_blocks_with_translation(self,
                                       blocks: List[DocumentBlock],
                                       translated_content: str,
                                       processor: DocumentProcessor) -> List[DocumentBlock]:
        """将整体翻译结果按顺序回填到可翻译块（用于非 RST 格式如 Markdown）"""
        translated_paragraphs = [p.strip() for p in translated_content.split('\n\n') if p.strip()]
        if not translated_paragraphs:
            translated_paragraphs = [p.strip() for p in translated_content.split('\n') if p.strip()]
        translated_index = 0
        updated_blocks: List[DocumentBlock] = []
        for block in blocks:
            if block.translatable and translated_index < len(translated_paragraphs):
                new_block = DocumentBlock(
                    type=block.type,
                    content=translated_paragraphs[translated_index],
                    translatable=True,
                    metadata=block.metadata.copy() if block.metadata else {}
                )
                if block.type == 'heading' and 'hashes' in block.metadata:
                    new_block.content = f"{block.metadata['hashes']} {translated_paragraphs[translated_index]}"
                elif block.type == 'list_item' and 'indent' in block.metadata:
                    indent = ' ' * block.metadata['indent']
                    marker = block.metadata['marker']
                    new_block.content = f"{indent}{marker} {translated_paragraphs[translated_index]}"
                elif block.type == 'blockquote':
                    new_block.content = f"> {translated_paragraphs[translated_index]}"
                updated_blocks.append(new_block)
                translated_index += 1
            else:
                updated_blocks.append(block)
        return updated_blocks

    def _attempt_retranslation_rst(self,
                                   original_blocks: List[DocumentBlock],
                                   translated_blocks: List[DocumentBlock],
                                   missing_content: str,
                                   max_targets: int = 5) -> Optional[List[DocumentBlock]]:
        """针对 RST 块定向重译改进缺失内容。
        返回更新后的 blocks 或 None。
        """
        if not missing_content or not missing_content.strip():
            return None
        try:
            # 1. 反向提取关键词
            reverse_prompt = ChatPromptTemplate.from_template(
                """
你是技术文档分析助手。请从下面关于缺失内容的中文描述中提取可能在英文原文中出现的关键词（英文术语、函数/结构名、文件名、协议名等）。
只输出逗号分隔的英文关键词，不要解释：

{missing}
"""
            )
            reverse_chain = reverse_prompt | self.translator.llm | TranslationOutputParser()
            try:
                keywords_raw = reverse_chain.invoke({"missing": missing_content})
                keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]
            except Exception:
                # import re as _re
                keywords = _re.findall(r'[A-Za-z][A-Za-z0-9_\-]+', missing_content)
            if not keywords:
                return None
            # 2. 匹配相关块
            scored: List[Tuple[int, int]] = []
            for idx, blk in enumerate(original_blocks):
                if not blk.translatable or not blk.content.strip():
                    continue
                text_lower = blk.content.lower()
                hits = sum(1 for kw in keywords if kw.lower() in text_lower)
                if hits > 0:
                    scored.append((idx, hits))
            if not scored:
                return None
            scored.sort(key=lambda x: x[1], reverse=True)
            primary_indices = [i for i, _ in scored[:max_targets]]
            # 3. 扩展上下文（左右各 1 个）
            context_indices = set()
            for i in primary_indices:
                for j in range(max(0, i - 1), min(len(original_blocks), i + 2)):
                    if original_blocks[j].translatable:
                        context_indices.add(j)
            expanded = sorted(context_indices)
            if not expanded:
                return None
            # 4. 构造片段文本
            segment_chunks = []
            for order, bi in enumerate(expanded, 1):
                segment_chunks.append(
                    f"[SEG-{order}]\n原文:\n{original_blocks[bi].content}\n当前译文:\n{translated_blocks[bi].content}"
                )
            segments_text = '\n\n-----\n\n'.join(segment_chunks)
            # 5. 重译 Prompt
            retranslate_prompt = ChatPromptTemplate.from_template(
                """
你是资深英文→简体中文技术翻译，需要对部分片段进行改进以补全遗漏内容：{missing_content}

要求：
1. 只改进提供的片段，不新增未提供原文的段落
2. 保留 RST 结构（标题、列表缩进、行内反引号、下划线/星号格式等）
3. 如果原译已正确可保持，但必须确保缺失信息被补足
4. 输出时严格按输入 [SEG-x] 的顺序，仅给出改进后的中文译文正文（不要输出 [SEG-x] 标识本身）
5. 片段之间使用独立分隔符 <<<END>>>

待改进片段：
{segments}

仅输出改进译文列表（每个译文之间用 <<<END>>> 分隔，不包含任何标记）：
"""
            )
            re_chain = retranslate_prompt | self.translator.llm | TranslationOutputParser()
            improved_all = re_chain.invoke({
                "missing_content": missing_content,
                "segments": segments_text
            })
            improved_parts = [p.strip() for p in improved_all.split('<<<END>>>') if p.strip()]
            if len(improved_parts) != len(expanded):
                fallback = [p.strip() for p in improved_all.split('\n\n') if p.strip()]
                if len(fallback) == len(expanded):
                    improved_parts = fallback
            if len(improved_parts) != len(expanded):
                return None
            # 清理 LLM 返回中可能残留的 [SEG-x] 标识
            cleaned_parts = []
            for part in improved_parts:
                # 移除开头的 [SEG-x] 或类似标识
                cleaned = _re.sub(r'^\s*\[SEG-\d+\]\s*', '', part)
                cleaned_parts.append(cleaned)
            improved_parts = cleaned_parts
            # 6. 应用替换
            new_blocks = translated_blocks.copy()
            for part, bi in zip(improved_parts, expanded):
                new_blocks[bi] = DocumentBlock(
                    type=new_blocks[bi].type,
                    content=part,
                    translatable=new_blocks[bi].translatable,
                    metadata=new_blocks[bi].metadata.copy() if new_blocks[bi].metadata else {}
                )
            return new_blocks
        except Exception as e:
            print(f"定向重译失败: {e}")
            return None

    def _full_retranslate_rst(self,
                              original_blocks: List[DocumentBlock],
                              translated_blocks: List[DocumentBlock],
                              missing_content: str) -> Optional[List[DocumentBlock]]:
        """整体重译 RST 的所有可翻译块，提示补全缺失内容。"""
        try:
            original_texts = [b.content for b in original_blocks if b.translatable and b.content.strip()]
            current_translated = [b.content for b in translated_blocks if b.translatable and b.content.strip()]
            orig_joined = '\n\n'.join(original_texts)
            trans_joined = '\n\n'.join(current_translated)
            prompt = ChatPromptTemplate.from_template(
                """
你是专业的英文→简体中文技术文档翻译改进器。下面是原文集合与当前译文集合。请在不破坏 RST 结构的前提下，输出改进后的完整译文集合，补全缺失信息：{missing}

要求：
1. 只输出改进后的所有译文段落，顺序与原文段落一致
2. 不添加额外说明、编号、标记
3. 维持原有段落粒度（使用双换行分隔）
4. 保留行内反引号、下划线、列表语法

【原文段落集合】
{original}

【当前译文段落集合】
{translated}

输出：改进后的译文段落集合（双换行分隔）：
"""
            )
            chain = prompt | self.translator.llm | TranslationOutputParser()
            improved_all = chain.invoke({
                "missing": missing_content,
                "original": orig_joined,
                "translated": trans_joined
            })
            improved_segments = [seg.strip() for seg in improved_all.split('\n\n') if seg.strip()]
            if not improved_segments:
                return None
            # 回填（按出现顺序）
            new_blocks: List[DocumentBlock] = []
            seg_idx = 0
            for b in translated_blocks:
                if b.translatable and b.content.strip() and seg_idx < len(improved_segments):
                    new_blocks.append(DocumentBlock(
                        type=b.type,
                        content=improved_segments[seg_idx],
                        translatable=True,
                        metadata=b.metadata.copy() if b.metadata else {}
                    ))
                    seg_idx += 1
                else:
                    new_blocks.append(b)
            return new_blocks
        except Exception as e:
            print(f"整体重译失败: {e}")
            return None
    
    def _update_metadata(self, metadata: Dict) -> Dict:
        """
        更新文档元数据
        
        Args:
            metadata: 原始元数据
            
        Returns:
            更新后的元数据
        """
        
        updated = metadata.copy()
        
        # 更新通用字段
        if 'status' in updated:
            updated['status'] = 'translated'
        if 'translator' in updated:
            updated['translator'] = self.translator_id
        if 'translating_date' in updated or 'translated_date' in updated:
            date_key = 'translating_date' if 'translating_date' in updated else 'translated_date'
            updated[date_key] = datetime.now().strftime("%Y%m%d")
        
        return updated
    
    def _append_translation_signature(self, content: str, file_ext: str) -> str:
        """在文档末尾添加翻译署名
        
        Args:
            content: 文档内容
            file_ext: 文件扩展名（.md, .rst 等）
            
        Returns:
            添加署名后的文档内容
        """
        signature = "\n\n由 Qwen-plus 及 LT agent 翻译"
        
        # RST 格式：可考虑加分隔符
        if file_ext in ['.rst']:
            signature = "\n\n" + "=" * 50 + "\n\n由 Qwen-plus 及 LT agent 翻译"
        
        return content + signature
    
    def _save_translation_stats(self, stats: Dict, stats_file: str):
        """保存翻译统计信息"""
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f"统计信息已保存: {stats_file}")
    
    def batch_translate(self,
                       input_dir: str,
                       output_dir: Optional[str] = None,
                       file_pattern: str = "*.*") -> List[Dict]:
        """
        批量翻译目录中的文件
        
        Args:
            input_dir: 输入目录
            output_dir: 输出目录（可选）
            file_pattern: 文件匹配模式
            
        Returns:
            翻译结果列表
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
        if output_dir is None:
            output_dir = str(input_path / "translated")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 查找所有支持的文件
        supported_extensions = ProcessorFactory.get_supported_extensions()
        files_to_translate = []
        
        for ext in supported_extensions:
            pattern = f"*{ext}" if file_pattern == "*.*" else file_pattern
            files_to_translate.extend(input_path.glob(pattern))
        
        if not files_to_translate:
            print(f"在 {input_dir} 中没有找到支持的文件")
            print(f"支持的格式: {', '.join(supported_extensions)}")
            return []
        
        print(f"找到 {len(files_to_translate)} 个文件待翻译")
        
        results = []
        for i, file_path in enumerate(files_to_translate, 1):
            print(f"\n[{i}/{len(files_to_translate)}] 处理文件: {file_path.name}")
            
            try:
                output_file = str(output_path / f"{file_path.stem}_translated{file_path.suffix}")
                stats = self.translate_file(
                    input_file=str(file_path),
                    output_file=output_file,
                    save_stats=True
                )
                results.append(stats)
            except Exception as e:
                print(f"翻译文件 {file_path.name} 时出错: {e}")
                results.append({
                    "input_file": str(file_path),
                    "error": str(e)
                })
        
        return results
    
    def get_translation_report(self, stats: Dict) -> str:
        """生成翻译报告"""
        lines = [
            "=" * 60,
            "翻译报告",
            "=" * 60,
            f"输入文件: {stats.get('input_file', 'N/A')}",
            f"输出文件: {stats.get('output_file', 'N/A')}",
            f"文件格式: {stats.get('file_format', 'N/A')}",
            f"翻译者: {stats.get('translator_id', 'N/A')}",
            "",
            "文档统计:",
            f"  总块数: {stats.get('total_blocks', 'N/A')}",
            f"  可翻译块: {stats.get('translatable_blocks', 'N/A')}",
            f"  分块数: {stats.get('chunk_count', 'N/A')}",
            "",
            "质量评估:",
            f"  完整性评分: {stats.get('completeness_score', 'N/A')}/10",
            "",
            "原文摘要:",
            f"  {stats.get('original_summary', 'N/A')}",
            "",
            "译文摘要:",
            f"  {stats.get('translated_summary', 'N/A')}",
            "",
            "=" * 60
        ]
        
        return '\n'.join(lines)
