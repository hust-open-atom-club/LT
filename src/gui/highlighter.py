# src/gui/highlighter.py
import re
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

class RSTHighlighter(QSyntaxHighlighter):
    """RST 语法高亮器 (增强版)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mapping = {}

        # 1. 标题和装饰线 (====, ----, ~~~~, ^^^^, ****)
        # 支持更多 RST 装饰符
        heading_format = QTextCharFormat()
        heading_format.setForeground(QColor("#61afef"))  # 蓝色
        heading_format.setFontWeight(QFont.Bold)
        # 匹配至少2个连续的标点符号作为装饰线
        self._mapping[r'^([-=~`:\'"^_*+#<>])\1+\s*$'] = heading_format

        # 2. 指令 (.. code-block::, .. image::)
        # 修正：使用 [\w-]+ 允许字母、数字、下划线和连字符
        directive_format = QTextCharFormat()
        directive_format.setForeground(QColor("#c678dd"))  # 紫色
        directive_format.setFontItalic(True)
        self._mapping[r'^\.\.\s+[\w-]+::'] = directive_format

        # 3. 字段列表 (:Field:)
        field_format = QTextCharFormat()
        field_format.setForeground(QColor("#98c379"))  # 绿色
        self._mapping[r'^:\w+:'] = field_format

        # 4. 代码块标记 (::)
        code_marker_format = QTextCharFormat()
        code_marker_format.setForeground(QColor("#e06c75"))  # 红色
        self._mapping[r'::$'] = code_marker_format
        
        # 5. 行内代码 (``text``)
        inline_code_format = QTextCharFormat()
        inline_code_format.setForeground(QColor("#e5c07b"))  # 黄色
        inline_code_format.setBackground(QColor("#3e4451"))  # 深灰色背景
        self._mapping[r'``.+?``'] = inline_code_format

        # 6. 列表项 (1., -, *, +)
        list_format = QTextCharFormat()
        list_format.setForeground(QColor("#d19a66"))  # 橙色
        list_format.setFontWeight(QFont.Bold)
        # 匹配无序列表 (*, -, +) 和 有序列表 (1., 1), (1))
        self._mapping[r'^\s*([-*+]|\(?\d+[.)])\s+'] = list_format

    def highlightBlock(self, text):
        for pattern, fmt in self._mapping.items():
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)
