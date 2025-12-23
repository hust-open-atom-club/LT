"""
翻译代理主函数
"""

import os
import shlex
import sys
import argparse
import glob
from pathlib import Path
from typing import List,Optional
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.translation_agent import TranslationAgent
from src.core.universal_translator import UniversalTranslator
from src.core.document_processor import ProcessorFactory


def setup_environment():
    """设置环境"""
    load_dotenv()
    
    from src.utils.config import config_manager
    
    config_file = Path("config.ini")
    if not config_file.exists():
        example_file = Path("config.ini.example")
        if example_file.exists():
            print(f"未找到配置文件，请复制 {example_file} 为 {config_file}")
            print("或者通过命令行参数直接传递API密钥")
        else:
            print("未找到配置文件，请通过命令行参数传递API密钥")
            print("   或使用环境变量配置（向后兼容）")
    else:
        print(f"已找到配置文件: {config_file}")


def parse_input_paths(raw_inputs: List[str]) -> List[Path]:
    """解析输入路径并校验存在性，支持通配符"""
    resolved: List[Path] = []
    for raw in raw_inputs:
        expanded = [Path(p) for p in glob.glob(raw)]
        if expanded:
            resolved.extend(expanded)
            continue

        path = Path(raw)
        if path.exists():
            resolved.append(path)
        else:
            print(f"输入路径不存在或未匹配任何文件: {raw}")
            sys.exit(1)

    if not resolved:
        print("未解析到任何输入文件，请检查路径或通配符")
        sys.exit(1)

    unique_paths: List[Path] = []
    seen = set()
    for path in resolved:
        resolved_path = path.resolve()
        if not resolved_path.is_file():
            print(f"路径不是文件或无法读取: {resolved_path}")
            sys.exit(1)
        key = str(resolved_path)
        if key not in seen:
            seen.add(key)
            unique_paths.append(resolved_path)

    return unique_paths

def calculate_output_path(input_path: Path, output_arg: Optional[str], is_batch: bool) -> Path:
    """
    智能计算输出路径
    
    Args:
        input_path: 输入文件路径
        output_arg: 命令行传入的 -o 参数
        is_batch: 是否为批量处理模式（多个输入文件）
    """
    suffix = f"_translated{input_path.suffix}"

    if not output_arg:
        default_dir = input_path.parent / "translations"
        
        if not default_dir.exists():
            default_dir.mkdir(parents=True, exist_ok=True)
            
        return default_dir / f"{input_path.stem}{suffix}"
    
    output_path = Path(output_arg)

    if is_batch:
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        elif output_path.is_file():
            print(f"错误: 批量翻译时，输出路径 '{output_arg}' 不能是文件，必须是目录或留空。")
            sys.exit(1)
        
        return output_path / f"{input_path.stem}{suffix}"

    # 情况3: 单文件模式
    else:
        # 如果 output_arg 看起来像目录 (以路径分隔符结尾，或者已存在且是目录)
        if output_arg.endswith(os.sep) or (output_path.exists() and output_path.is_dir()):
            output_path.mkdir(parents=True, exist_ok=True)
            return output_path / f"{input_path.stem}{suffix}"

        # 否则视为具体的文件路径
        # 确保父目录存在
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

def run_translation_task(args):
    """统一的翻译任务执行入口"""
    # 1. 解析所有输入路径
    input_paths = parse_input_paths(args.inputs)
    is_batch = len(input_paths) > 1
    
    print(f"启动翻译任务")
    print(f"待处理文件数: {len(input_paths)}")
    
    # 初始化翻译器
    translator = UniversalTranslator(
        model_name=args.model,
        translator_id=args.translator,
        max_tokens=args.max_tokens,
        provider=args.provider,
        openai_api_key=getattr(args, 'openai_api_key', None),
        openai_base_url=getattr(args, 'openai_base_url', None),
        qwen_api_key=getattr(args, 'qwen_api_key', None)
    )
    
    results = []
    
    # 2. 统一循环逻辑
    for i, input_path in enumerate(input_paths):
        print(f"\n[{i+1}/{len(input_paths)}] 处理: {input_path.name}")
        
        try:
            # 计算当前文件的输出路径
            output_path = calculate_output_path(input_path, args.output, is_batch)
            
            # 调用翻译器 (write_to_disk=True 因为是CLI模式)
            stats = translator.translate_file(
                input_file=str(input_path),
                output_file=str(output_path),
                save_stats=True,
                write_to_disk=True
            )
            
            # 终端模式下打印报告
            report_text = translator.get_translation_report(stats)
            print(report_text)
            results.append(stats)
            
        except Exception as e:
            print(f"   -> 失败: {e}")
            results.append({
                "input_file": str(input_path),
                "error": str(e)
            })
            # 如果不是批量模式，且出错，直接退出
            if not is_batch:
                sys.exit(1)

    # 3. 批量模式下的汇总报告
    if is_batch and results:
        successful = sum(1 for r in results if 'error' not in r)
        total = len(results)

        # 计算平均分
        valid_scores = [r.get('completeness_score', 0) for r in results if 'error' not in r]
        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0

        print(f"\n{'='*30}")
        print(f"任务完成汇总")
        print(f"成功: {successful}/{total}")
        print(f"平均完整性评分: {avg_score:.1f}/10")

        # 如果指定了输出目录，可以在那里生成一个总的 json 报告
        if args.output and os.path.isdir(args.output):
            report_path = Path(args.output) / "batch_report.json"
            import json
            with open(report_path, 'w', encoding='utf-8') as f:
                # 剔除内容过大的字段以免报告文件太大
                clean_results = []
                for r in results:
                    r_copy = r.copy()
                    r_copy.pop('translated_content', None) # 报告里不需要全文
                    r_copy.pop('original_summary', None)
                    r_copy.pop('translated_summary', None)
                    clean_results.append(r_copy)
                json.dump(clean_results, f, ensure_ascii=False, indent=2)
            print(f"汇总报告已生成: {report_path}")
            
def validate_translation(args):
    """验证翻译质量"""
    print(f"验证翻译质量")
    
    # 翻译代理
    agent = TranslationAgent(
        translator_id=args.translator,
        provider=args.provider,
        openai_api_key=getattr(args, 'openai_api_key', None),
        openai_base_url=getattr(args, 'openai_base_url', None),
        qwen_api_key=getattr(args, 'qwen_api_key', None)
    )
    
    try:
        result = agent.validate_translation(args.original, args.translated)
    
        print(f"\n翻译质量报告:")
        print(f"   质量评分: {result['validation_score']}/10")
        print(f"   遗漏内容: {result['comparison_result'].get('missing_content', '无')}" )
        print(f"   改进建议: {result['comparison_result'].get('suggestions', '无')}" )
    
    except Exception as e:
        print(f"验证过程中发生错误: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="智能翻译代理 - 长文本英译汉工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 翻译单个 Markdown 文件
  python main.py translate input.md -o output.md
  
  # 翻译单个 RST 文件
  python main.py translate input.rst -o output.rst
  
  # 翻译多个文件或使用通配符
  python main.py translate docs/*.md
  
  # 验证翻译质量
  python main.py validate original.md translated.md
  
支持的文件格式:
  - Markdown (.md, .markdown)
  - reStructuredText (.rst, .rest)
  
环境配置:
  请复制.env.example为.env并配置您的OpenAI API密钥
        """
    )
    
    parser.add_argument(
        '--model',
        default='gpt-3.5-turbo',
        help='使用的模型名称 (默认: gpt-3.5-turbo)'
    )
    
    parser.add_argument(
        '--provider',
        choices=['openai', 'qwen', 'auto'],
        default='auto',
        help='模型提供商 (openai, qwen, auto) (默认: auto)'
    )
    
    parser.add_argument(
        '--translator',
        default='FILL_YOUR_GITHUB_ID_HERE',
        help='翻译者ID (默认: FILL_YOUR_GITHUB_ID_HERE)'
    )
    
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=800,
        help='每个文本块的最大token数 (默认: 800)'
    )
    
    parser.add_argument(
        '--openai-api-key',
        help='OpenAI API密钥（优先级高于配置文件）'
    )
    
    parser.add_argument(
        '--openai-base-url',
        help='OpenAI API基础URL（优先级高于配置文件）'
    )
    
    parser.add_argument(
        '--qwen-api-key',
        help='Qwen API密钥（优先级高于配置文件）'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    translate_parser = subparsers.add_parser(
        'translate', 
        aliases=['t'], 
        help='翻译文件（支持通配符和多文件）'
    )
    translate_parser.add_argument('inputs', nargs='+', help='输入文件路径（可包含通配符）')
    translate_parser.add_argument('-o', '--output', help='输出文件路径（单文件）或输出目录（多文件）')

    validate_parser = subparsers.add_parser(
        'validate', 
        aliases=['v'], 
        help='验证翻译质量'
    )
    validate_parser.add_argument('original', help='原始文件路径')
    validate_parser.add_argument('translated', help='翻译文件路径')

    raw = sys.argv[1:]

    # 如果只收到一个参数，而且里面有空格，认为是 VSCode 传进来的“整行命令”,方便vscode调试
    if len(raw) == 1 and " " in raw[0]:
        raw = shlex.split(raw[0])

    args = parser.parse_args(raw)

    if not args.command:
        parser.print_help()
        return
    
    setup_environment()

    if args.command in ['translate', 't']:
        run_translation_task(args)
    elif args.command == ['validate', 'v']:
        validate_translation(args)

if __name__ == "__main__":
    main()
