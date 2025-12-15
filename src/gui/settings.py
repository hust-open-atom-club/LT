# src/gui/settings.py
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QDialogButtonBox, QLabel
)
from PySide6.QtCore import QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(450, 350)
        
        # 1. 计算 config.ini 的绝对路径
        # 当前文件在 src/gui/settings.py
        # 向上一级 src/gui -> src -> 项目根目录
        root_dir = Path(__file__).parent.parent.parent
        config_path = root_dir / "config.ini"
        
        # 2. 初始化 QSettings 为 INI 模式，并指定路径
        # QSettings.Format.IniFormat 强制使用文件模式
        self.settings = QSettings(str(config_path), QSettings.Format.IniFormat)
        
        # 强制不使用系统默认的存储位置，而是我们指定的文件
        print(f"配置文件路径: {config_path}")

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Provider
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["auto", "openai", "qwen"])
        self.combo_provider.setToolTip("选择模型提供商")
        form_layout.addRow("提供商 (Provider):", self.combo_provider)

        # Model Name
        self.line_model = QLineEdit()
        self.line_model.setPlaceholderText("例如: gpt-3.5-turbo, qwen-plus")
        form_layout.addRow("模型名称 (Model):", self.line_model)

        # 分割线
        layout.addLayout(form_layout)
        layout.addSpacing(10)
        
        # OpenAI Config Group
        lbl_openai = QLabel("OpenAI 配置:")
        lbl_openai.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_openai)
        
        openai_layout = QFormLayout()
        self.line_openai_key = QLineEdit()
        self.line_openai_key.setEchoMode(QLineEdit.Password)
        self.line_openai_key.setPlaceholderText("sk-...")
        openai_layout.addRow("API Key:", self.line_openai_key)

        self.line_openai_base = QLineEdit()
        self.line_openai_base.setPlaceholderText("https://api.openai.com/v1")
        openai_layout.addRow("Base URL:", self.line_openai_base)
        layout.addLayout(openai_layout)

        # Qwen Config Group
        lbl_qwen = QLabel("Qwen (通义千问) 配置:")
        lbl_qwen.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_qwen)
        
        qwen_layout = QFormLayout()
        self.line_qwen_key = QLineEdit()
        self.line_qwen_key.setEchoMode(QLineEdit.Password)
        self.line_qwen_key.setPlaceholderText("sk-...")
        qwen_layout.addRow("API Key:", self.line_qwen_key)
        layout.addLayout(qwen_layout)
        
        # 说明
        hint = QLabel(f"配置将保存至项目根目录的 config.ini")
        hint.setStyleSheet("color: gray; font-size: 11px; margin-top: 10px;")
        layout.addWidget(hint)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_settings(self):
        """加载配置到 UI"""
        # 注意：这里使用 '/' 来访问 INI 的 Section，例如 default/provider 对应 [default] 下的 provider
        
        # [default] section
        self.combo_provider.setCurrentText(self.settings.value("default/provider", "auto"))
        self.line_model.setText(self.settings.value("default/model_name", "gpt-3.5-turbo"))
        
        # [openai] section
        self.line_openai_key.setText(self.settings.value("openai/api_key", ""))
        self.line_openai_base.setText(self.settings.value("openai/base_url", ""))
        
        # [qwen] section
        self.line_qwen_key.setText(self.settings.value("qwen/api_key", ""))

    def save_settings(self):
        """保存 UI 配置到本地 config.ini"""
        
        # 写入 [default]
        self.settings.setValue("default/provider", self.combo_provider.currentText())
        self.settings.setValue("default/model_name", self.line_model.text().strip())
        
        # 写入 [openai]
        self.settings.setValue("openai/api_key", self.line_openai_key.text().strip())
        # 如果 base_url 为空，可以选择不写或者写空字符串，这里写空字符串方便后续读取
        self.settings.setValue("openai/base_url", self.line_openai_base.text().strip())
        
        # 写入 [qwen]
        self.settings.setValue("qwen/api_key", self.line_qwen_key.text().strip())
        
        # 强制同步写入磁盘
        self.settings.sync()
        
        self.accept()

    def get_config_dict(self):
        """获取供 Worker 使用的字典 (实时从文件读取)"""
        # 确保读取最新数据
        self.settings.sync()
        
        return {
            "provider": self.settings.value("default/provider", "auto"),
            "model_name": self.settings.value("default/model_name", "gpt-3.5-turbo"),
            "openai_api_key": self.settings.value("openai/api_key", ""),
            "openai_base_url": self.settings.value("openai/base_url", ""),
            "qwen_api_key": self.settings.value("qwen/api_key", ""),
            "translator_id": "GUI_User"
        }
