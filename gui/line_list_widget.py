from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QListWidget, QListWidgetItem, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt

class LineListWidget(QWidget):
    showHideToggled = pyqtSignal(int, bool)  # index, visible
    removeRequested = pyqtSignal(int)        # index
    editRequested = pyqtSignal(int)          # index (for editing params)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.list_widget = QListWidget()
        self.vbox.addWidget(self.list_widget)
        self.line_items = []  # Store (widget, QListWidgetItem)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(0, 0)
        self.vbox.setStretch(0, 0)

    def add_line(self, label, visible=True):
        widget = QWidget()
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        checkbox = QCheckBox()
        checkbox.setChecked(visible)
        hbox.addWidget(checkbox)
        lbl = QLabel(label)
        hbox.addWidget(lbl)
        hbox.addStretch(1)
        remove_btn = QPushButton("Remove")
        remove_btn.setMaximumWidth(60)
        hbox.addWidget(remove_btn)
        widget.setLayout(hbox)
        item = QListWidgetItem()
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        item.setSizeHint(widget.sizeHint())
        idx = self.list_widget.count() - 1
        self.line_items.append((widget, item))
        # Connect signals
        checkbox.toggled.connect(lambda checked, i=idx: self.showHideToggled.emit(i, checked))
        remove_btn.clicked.connect(lambda _, i=idx: self.removeRequested.emit(i))

    def _on_item_double_clicked(self, item):
        idx = self.list_widget.row(item)
        self.editRequested.emit(idx)

    def remove_line(self, idx):
        if 0 <= idx < len(self.line_items):
            _, item = self.line_items.pop(idx)
            self.list_widget.takeItem(idx)
            # Re-index remaining items
            for i, (widget, item) in enumerate(self.line_items):
                pass

    def set_line_visible(self, idx, visible):
        if 0 <= idx < len(self.line_items):
            widget, item = self.line_items[idx]
            checkbox = widget.layout().itemAt(0).widget()
            checkbox.setChecked(visible)

    def clear(self):
        self.list_widget.clear()
        self.line_items.clear() 