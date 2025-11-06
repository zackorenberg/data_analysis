from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextOption
from PyQt5.QtCore import Qt, QTimer

class QCompactTextEdit(QTextEdit):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setText(text)

        self.setWordWrapMode(QTextOption.WrapAnywhere)
        self.setLineWrapMode(QTextEdit.WidgetWidth)

        #self.setFrameStyle(QTextEdit.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QTextEdit { background: transparent; margin: 0px; padding: 0px; border: none; }")
        self.setViewportMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)

        QTimer.singleShot(0, self.adjustHeight)

    def adjustHeight(self):
        doc = self.document()
        doc.setTextWidth(self.viewport().width())
        height = doc.size().height()
        self.setFixedHeight(int(height))