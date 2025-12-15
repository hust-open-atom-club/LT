# src/gui/worker.py
import sys
import os
import traceback
from PySide6.QtCore import QThread, Signal

# 引入你的核心逻辑
from src.core.universal_translator import UniversalTranslator

class TranslationWorker(QThread):
    """
    后台翻译线程
    """
    # 信号：翻译完成 (文件路径, 结果字典)
    finished_signal = Signal(str, dict)
    # 信号：发生错误 (文件路径, 错误信息)
    error_signal = Signal(str, str)
    # 信号：日志输出 (可选，用于更新界面进度条或状态栏)
    log_signal = Signal(str)

    def __init__(self, input_path, output_path, config):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.config = config

    def run(self):
        try:
            self.log_signal.emit(f"开始翻译: {os.path.basename(self.input_path)}")
            
            # 初始化翻译器 (利用传入的配置)
            translator = UniversalTranslator(
                model_name=self.config.get('model_name', 'gpt-3.5-turbo'),
                provider=self.config.get('provider', 'auto'),
                translator_id=self.config.get('translator_id', 'GUI_User'),
                openai_api_key=self.config.get('openai_api_key'),
                openai_base_url=self.config.get('openai_base_url'),
                qwen_api_key=self.config.get('qwen_api_key')
            )

            # 调用核心翻译逻辑
            # write_to_disk=True 保证生成文件，同时 stats 中包含 'translated_content'
            stats = translator.translate_file(
                input_file=self.input_path,
                output_file=self.output_path,
                save_stats=True,
                write_to_disk=True 
            )

            self.finished_signal.emit(self.input_path, stats)

        except Exception as e:
            error_msg = f"翻译失败: {str(e)}\n{traceback.format_exc()}"
            self.error_signal.emit(self.input_path, error_msg)
