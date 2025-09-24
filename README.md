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
- `src/config_manager.py` — Configuration and API key management.
- `tests/` — Various test scripts.
- `requirements.txt` — Python dependencies.
- `main.py` — Command-line interface for translation.
  
## Attention

The api key is configured in `config.ini`.


## Run locally
```
git clone https://github.com/open-atom-hust-club/LT.git
cd LT
pdm install
python main.py --model qwen-plus --provider qwen translate tests/ldm.md -o tests/ldm_translated.md
```

