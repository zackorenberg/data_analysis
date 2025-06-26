from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QListWidget, QListWidgetItem, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt
from logger import get_logger

logger = get_logger(__name__)

class LineListWidget(QWidget):
    showHideToggled = pyqtSignal(int, bool)  # index, visible
    removeRequested = pyqtSignal(int)        # index
    editRequested = pyqtSignal(int)          # index (for editing params)

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug('LineListWidget initialized')
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
        logger.debug(f'Adding line: {label}, visible={visible}')
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
        logger.info(f'Line added: {label}')

    def _on_item_double_clicked(self, item):
        idx = self.list_widget.row(item)
        logger.debug(f'Double-clicked line idx={idx}')
        self.editRequested.emit(idx)

    def remove_line(self, idx):
        logger.debug(f'Removing line idx={idx}')
        if 0 <= idx < len(self.line_items):
            _, item = self.line_items.pop(idx)
            self.list_widget.takeItem(idx)
            logger.info(f'Line removed idx={idx}')
            # Re-index remaining items
            for i, (widget, item) in enumerate(self.line_items):
                pass
        else:
            logger.error(f'Tried to remove invalid line idx={idx}')

    def set_line_visible(self, idx, visible):
        logger.debug(f'Setting line idx={idx} visible={visible}')
        if 0 <= idx < len(self.line_items):
            widget, item = self.line_items[idx]
            checkbox = widget.layout().itemAt(0).widget()
            checkbox.setChecked(visible)
            logger.info(f'Line visibility set idx={idx} visible={visible}')
        else:
            logger.error(f'Tried to set visibility for invalid line idx={idx}')

    def clear(self):
        logger.debug('Clearing all lines from LineListWidget')
        self.list_widget.clear()
        self.line_items.clear()
        logger.info('All lines cleared from LineListWidget') 