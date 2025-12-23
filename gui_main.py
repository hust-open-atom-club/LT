# gui_main.py
import sys
import os

# 将 src 加入路径，确保能导入 core 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from src.gui.app import MainWindow
from src.core.document_processor import ProcessorFactory
from src.core.markdown_document_processor import MarkdownDocumentProcessor
from src.core.rst_processor import RSTProcessor

def register_processors():
    """确保文档处理器已注册"""
    # 虽然 __init__.py 里可能注册了，但显式调用更安全
    ProcessorFactory.register(['.md', '.markdown'], MarkdownDocumentProcessor)
    ProcessorFactory.register(['.rst', '.rest'], RSTProcessor)

def main():
    # 1. 设置环境
    from dotenv import load_dotenv
    load_dotenv()
    
    # 2. 注册处理器
    register_processors()

    # 3. 启动 GUI
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
