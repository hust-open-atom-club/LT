# src/gui/app.py
import os
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPlainTextEdit, QPushButton, QSplitter, 
    QFileDialog, QLabel, QMessageBox, QProgressBar, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent

import qdarktheme

from .worker import TranslationWorker
from .highlighter import RSTHighlighter
from .settings import SettingsDialog  # 导入新写的设置对话框

class FileItem:
    """数据类：管理单个文件的状态"""
    def __init__(self, path: str):
        self.input_path = path
        self.file_name = os.path.basename(path)
        p = Path(path)
        self.output_path = str(p.parent / f"{p.stem}_translated{p.suffix}")
        
        self.source_content: str = ""
        self.translated_content: Optional[str] = None
        self.is_translating = False
        self.error_msg: Optional[str] = None
        
        self._load_source()
        self._try_load_existing_translation()

    def _load_source(self):
        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                self.source_content = f.read()
        except Exception as e:
            self.source_content = f"读取失败: {e}"

    def _try_load_existing_translation(self):
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    self.translated_content = f.read()
            except:
                self.translated_content = None

class DragDropListWidget(QListWidget):
    """支持文件拖拽的列表控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDrop)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setStyleSheet("QListWidget { padding: 5px; font-size: 14px; border: 1px solid #3f3f3f; }")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            self.window().add_files(files)
            event.accept()
        else:
            super().dropEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LT - 智能翻译代理 (GUI v1.1)")
        self.resize(1200, 800)
        
        # 数据存储
        self.file_map: Dict[str, FileItem] = {}
        self.current_file_path: Optional[str] = None
        self.is_busy = False 
        
        # 预加载设置弹窗对象，但不显示
        self.settings_dialog = SettingsDialog(self)

        self.setup_ui()
        self.setup_theme()
        
        # 初始化按钮状态
        self.update_translate_button_state()

    def setup_theme(self):
        qdarktheme.setup_theme("dark")

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # === 左侧边栏 ===
        sidebar_layout = QVBoxLayout()
        
        lbl_files = QLabel("📄 文件列表")
        lbl_files.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        sidebar_layout.addWidget(lbl_files)

        self.file_list_widget = DragDropListWidget()
        self.file_list_widget.currentItemChanged.connect(self.on_file_selection_changed)
        sidebar_layout.addWidget(self.file_list_widget)

        # 按钮区域
        btn_add = QPushButton("添加文件 (+)")
        btn_add.clicked.connect(self.open_file_dialog)
        btn_add.setStyleSheet("background-color: #3e4451; height: 30px;")
        
        btn_settings = QPushButton("⚙ 设置 API Key")
        btn_settings.clicked.connect(self.open_settings)
        btn_settings.setStyleSheet("background-color: #3e4451; height: 30px;")
        
        btn_clear = QPushButton("清空列表")
        btn_clear.clicked.connect(self.clear_all)
        btn_clear.setStyleSheet("height: 30px;")

        self.btn_translate = QPushButton("开始翻译")
        self.btn_translate.clicked.connect(self.start_translation)
        # 设置固定高度
        self.btn_translate.setFixedHeight(45)
        # 初始样式设置（稍后由 update_translate_button_state 覆盖）
        self.btn_translate.setStyleSheet("font-weight: bold; font-size: 14px;")

        sidebar_layout.addWidget(btn_add)
        sidebar_layout.addWidget(btn_settings)
        sidebar_layout.addWidget(btn_clear)
        sidebar_layout.addSpacing(10)
        sidebar_layout.addWidget(self.btn_translate)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        sidebar_layout.addWidget(self.progress_bar)

        sidebar_container = QWidget()
        sidebar_container.setLayout(sidebar_layout)
        sidebar_container.setFixedWidth(260)
        main_layout.addWidget(sidebar_container)

        # === 右侧编辑器 ===
        editor_splitter = QSplitter(Qt.Horizontal)
        
        # 原文
        source_container = QWidget()
        source_layout = QVBoxLayout(source_container)
        source_layout.setContentsMargins(0,0,0,0)
        lbl_source = QLabel("原文 (Source)")
        lbl_source.setStyleSheet("color: #abb2bf; font-weight: bold; padding: 5px;")
        self.editor_source = QPlainTextEdit()
        self.editor_source.setReadOnly(True)
        self.editor_source.setPlaceholderText("请拖拽文件到左侧列表...")
        self.source_highlighter = RSTHighlighter(self.editor_source.document())
        
        source_layout.addWidget(lbl_source)
        source_layout.addWidget(self.editor_source)

        # 译文
        target_container = QWidget()
        target_layout = QVBoxLayout(target_container)
        target_layout.setContentsMargins(0,0,0,0)
        lbl_target = QLabel("译文 (Translation)")
        lbl_target.setStyleSheet("color: #98c379; font-weight: bold; padding: 5px;")
        self.editor_target = QPlainTextEdit()
        self.editor_target.setReadOnly(False)
        self.editor_target.setPlaceholderText("等待翻译...")
        self.target_highlighter = RSTHighlighter(self.editor_target.document())

        target_layout.addWidget(lbl_target)
        target_layout.addWidget(self.editor_target)

        editor_splitter.addWidget(source_container)
        editor_splitter.addWidget(target_container)
        editor_splitter.setSizes([450, 450])

        main_layout.addWidget(editor_splitter, stretch=1)

    def update_translate_button_state(self):
        """核心逻辑：更新按钮的颜色和可用性"""
        has_selection = self.file_list_widget.currentRow() != -1
        
        if self.is_busy:
            # 翻译中：禁用
            self.btn_translate.setEnabled(False)
            self.btn_translate.setText("翻译中...")
            self.btn_translate.setStyleSheet("""
                QPushButton {
                    background-color: #4b5263;
                    color: #abb2bf;
                    border: none;
                    border-radius: 4px;
                }
            """)
        elif has_selection:
            # 有选中且空闲：高亮
            self.btn_translate.setEnabled(True)
            self.btn_translate.setText("开始翻译")
            # 亮色背景，纯白文字，加粗
            self.btn_translate.setStyleSheet("""
                QPushButton {
                    background-color: #61afef; 
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 14px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #528bff;
                }
                QPushButton:pressed {
                    background-color: #3d6ac4;
                }
            """)
        else:
            # 无选中：灰色
            self.btn_translate.setEnabled(False)
            self.btn_translate.setText("开始翻译")
            self.btn_translate.setStyleSheet("""
                QPushButton {
                    background-color: #2c323a;
                    color: #5c6370;
                    border: 1px solid #3e4451;
                    border-radius: 4px;
                }
            """)

    def add_files(self, file_paths):
        if self.is_busy: return
        for path in file_paths:
            path = str(path)
            if not os.path.isfile(path): continue
            if path in self.file_map: continue
            
            item_data = FileItem(path)
            self.file_map[path] = item_data
            
            list_item = QListWidgetItem(item_data.file_name)
            list_item.setData(Qt.UserRole, path)
            list_item.setToolTip(path)
            self.file_list_widget.addItem(list_item)

        if self.file_list_widget.count() > 0 and self.file_list_widget.currentRow() == -1:
            self.file_list_widget.setCurrentRow(0)
        
        self.update_translate_button_state()

    def open_file_dialog(self):
        if self.is_busy: return
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "", "Documents (*.md *.rst *.txt);;All Files (*)"
        )
        if paths:
            self.add_files(paths)

    def open_settings(self):
        """打开设置窗口"""
        if self.is_busy: return
        self.settings_dialog.load_settings() # 刷新显示
        self.settings_dialog.exec()

    def clear_all(self):
        if self.is_busy: return
        self.file_list_widget.clear()
        self.file_map.clear()
        self.editor_source.clear()
        self.editor_target.clear()
        self.current_file_path = None
        self.update_translate_button_state()

    def on_file_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if self.is_busy: return # 忙碌时不处理切换逻辑（UI已锁定）

        self.update_translate_button_state() # 刷新按钮状态

        if not current:
            self.current_file_path = None
            self.editor_source.clear()
            self.editor_target.clear()
            return

        file_path = current.data(Qt.UserRole)
        self.current_file_path = file_path
        file_item = self.file_map.get(file_path)

        if not file_item: return

        self.editor_source.setPlainText(file_item.source_content)

        if file_item.is_translating:
            self.editor_target.setPlainText("正在翻译中...")
            self.editor_target.setStyleSheet("background-color: #2c3e50; color: #e5c07b;")
        elif file_item.error_msg:
            self.editor_target.setPlainText(f"翻译出错:\n{file_item.error_msg}")
            self.editor_target.setStyleSheet("background-color: #3e2c2c; color: #e06c75;")
        elif file_item.translated_content:
            self.editor_target.setPlainText(file_item.translated_content)
            self.editor_target.setStyleSheet("") 
        else:
            self.editor_target.clear()
            self.editor_target.setPlaceholderText("尚未翻译。")
            self.editor_target.setStyleSheet("background-color: #252526;")

    def start_translation(self):
        if not self.current_file_path:
            QMessageBox.warning(self, "提示", "请先选择一个文件")
            return
        
        # 1. 获取配置
        config = self.settings_dialog.get_config_dict()
        provider = config.get("provider")
        
        # 2. 检查 Key 是否存在 (阻断逻辑)
        has_key = False
        if provider == "openai" and config.get("openai_api_key"):
            has_key = True
        elif provider == "qwen" and config.get("qwen_api_key"):
            has_key = True
        elif provider == "auto" and (config.get("openai_api_key") or config.get("qwen_api_key")):
            has_key = True
        
        if not has_key:
            reply = QMessageBox.question(
                self, "缺少配置", 
                "未检测到 API Key，无法开始翻译。\n是否现在去设置？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_settings()
            return

        file_item = self.file_map[self.current_file_path]
        
        self.set_ui_busy(True)
        
        file_item.is_translating = True
        file_item.error_msg = None
        
        self.editor_target.setPlainText("正在初始化翻译代理...\n请稍候...")
        self.editor_target.setStyleSheet("color: #e5c07b;")

        self.worker = TranslationWorker(
            file_item.input_path, 
            file_item.output_path,
            config # 传入实时配置
        )
        self.worker.finished_signal.connect(self.on_translation_finished)
        self.worker.error_signal.connect(self.on_translation_error)
        self.worker.start()

    def on_translation_finished(self, input_path, stats):
        item = self.file_map.get(input_path)
        if item:
            item.is_translating = False
            content = stats.get('translated_content')
            if not content and os.path.exists(item.output_path):
                with open(item.output_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            item.translated_content = content
        
        self.set_ui_busy(False)
        
        if self.current_file_path == input_path:
            self.editor_target.setPlainText(item.translated_content)
            self.editor_target.setStyleSheet("")
            QMessageBox.information(self, "完成", f"翻译完成！\n完整性评分: {stats.get('completeness_score', 0)}")

    def on_translation_error(self, input_path, error_msg):
        item = self.file_map.get(input_path)
        if item:
            item.is_translating = False
            item.error_msg = error_msg
        
        self.set_ui_busy(False)
        
        if self.current_file_path == input_path:
            self.editor_target.setPlainText(error_msg)
            self.editor_target.setStyleSheet("color: #e06c75;")
            QMessageBox.critical(self, "错误", "翻译过程中发生错误，请查看右侧详情。")

    def set_ui_busy(self, busy: bool):
        self.is_busy = busy
        self.file_list_widget.setEnabled(not busy)
        self.update_translate_button_state() # 更新按钮外观
        
        if busy:
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
