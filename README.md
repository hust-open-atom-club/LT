[![pdm-managed](https://img.shields.io/endpoint?url=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fpdm-project%2F.github%2Fbadge.json)](https://pdm-project.org)

# LT
LT(LLM Translator) is autonomous translate agent that helps with Linux Kernel docs' translation.
It supports block-based translation of large documents, translation integrity detection, and targeted retranslation (only retranslating missing segments to reduce costs).

## Project Structure

- `src/llm_factory.py` — Qwen/OpenAI client wrapper and `QwenChatModel`.
- `src/text_chunker.py` — Markdown chunker based on structure and token limits.
- `src/translator.py` — Main translation workflow: chunking, translation, merging, summary comparison, and focused retranslation.
- `src/summary_generator.py` — Generates summaries and performs source/translation comparison.
- `src/markdown_parser.py` — Parses YAML front matter and content.
- `src/rst_processor.py` — reStructuredText-specific processor (block parsing/reconstruction).
- `src/universal_translator.py` — 通用编排器，按文件格式选择处理器并管理逐块/整篇翻译与重译策略。
- `src/config_manager.py` — Configuration and API key management.
- `tests/` — Various test scripts.
- `requirements.txt` — Python dependencies.
- `main.py` — Command-line interface for translation.
  
## Attention

The api key is configured in `config.ini`.


## Run locally
```bash
git clone https://github.com/open-atom-hust-club/LT.git
cd LT
pdm install
python main.py --model qwen-plus --provider qwen translate tests/ldm.md -o tests/ldm_translated.md

# 单独运行 RST 测试（不会与 Markdown 的 `pdm run test` 冲突）
# 已在 `pyproject.toml` 中添加了一个独立脚本 `test-rst`：
```
pdm run test-rst
```
或显式运行：
```
pdm run python main.py --model qwen-plus --provider qwen translate tests/w1-generic.rst -o tests/w1-generic_translated.rst
```
```

## Testing

Run the translation test using PDM:
```bash
pdm test         # 运行 Markdown 测试 (ldm.md)
# 或运行 RST 专用测试：
pdm run test-rst  # 运行 RST 测试 (w1-generic.rst)
```

This command will translate the test Markdown file `tests/ldm.md` to `tests/ldm_translated.md` using the qwen-plus model.

