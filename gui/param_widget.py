from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QPushButton, QHBoxLayout, QLabel)
from PyQt5.QtCore import pyqtSignal

class ParamWidget(QDockWidget):
    paramsSelected = pyqtSignal(dict)
    requestUpdateParams = pyqtSignal()
    requestResetPlot = pyqtSignal()
    exportToMatplotlibRequested = pyqtSignal()

    def __init__(self, current_params=None, parent=None):
        super().__init__("Plot Options", parent)
        self.current_params = current_params or {}
        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout()
        form = QFormLayout()
        # Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Plot Title")
        if 'title' in self.current_params:
            self.title_edit.setText(self.current_params['title'])
        form.addRow("Title:", self.title_edit)
        # X label
        self.xlabel_edit = QLineEdit()
        self.xlabel_edit.setPlaceholderText("X Label")
        if 'xlabel' in self.current_params:
            self.xlabel_edit.setText(self.current_params['xlabel'])
        form.addRow("X Label:", self.xlabel_edit)
        # Y label
        self.ylabel_edit = QLineEdit()
        self.ylabel_edit.setPlaceholderText("Y Label")
        if 'ylabel' in self.current_params:
            self.ylabel_edit.setText(self.current_params['ylabel'])
        form.addRow("Y Label:", self.ylabel_edit)
        # X limits
        self.xlim_min = QLineEdit()
        self.xlim_min.setPlaceholderText("X min")
        self.xlim_max = QLineEdit()
        self.xlim_max.setPlaceholderText("X max")
        xlim_layout = QHBoxLayout()
        xlim_layout.addWidget(self.xlim_min)
        xlim_layout.addWidget(QLabel("to"))
        xlim_layout.addWidget(self.xlim_max)
        form.addRow("X Limits:", xlim_layout)
        # Y limits
        self.ylim_min = QLineEdit()
        self.ylim_min.setPlaceholderText("Y min")
        self.ylim_max = QLineEdit()
        self.ylim_max.setPlaceholderText("Y max")
        ylim_layout = QHBoxLayout()
        ylim_layout.addWidget(self.ylim_min)
        ylim_layout.addWidget(QLabel("to"))
        ylim_layout.addWidget(self.ylim_max)
        form.addRow("Y Limits:", ylim_layout)
        # Grid
        self.grid_check = QCheckBox("Show Grid")
        if 'grid' in self.current_params:
            self.grid_check.setChecked(self.current_params['grid'])
        form.addRow(self.grid_check)
        # Legend
        self.legend_check = QCheckBox("Show Legend")
        if 'legend' in self.current_params:
            self.legend_check.setChecked(self.current_params['legend'])
        else:
            self.legend_check.setChecked(True)
        form.addRow(self.legend_check)
        # X ticks
        self.xticks_edit = QLineEdit()
        self.xticks_edit.setPlaceholderText("Comma-separated (e.g. 0,1,2,3)")
        if 'xticks' in self.current_params:
            self.xticks_edit.setText(self.current_params['xticks'])
        form.addRow("X Ticks:", self.xticks_edit)
        # Y ticks
        self.yticks_edit = QLineEdit()
        self.yticks_edit.setPlaceholderText("Comma-separated (e.g. 0,1,2,3)")
        if 'yticks' in self.current_params:
            self.yticks_edit.setText(self.current_params['yticks'])
        form.addRow("Y Ticks:", self.yticks_edit)
        layout.addLayout(form)
        # Buttons
        btns = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        reset_btn = QPushButton("Reset")
        reload_btn = QPushButton("Reload")
        export_btn = QPushButton("Open in Matplotlib Window")
        apply_btn.clicked.connect(self.apply)
        reset_btn.clicked.connect(self.reset)
        reload_btn.clicked.connect(self.reload)
        export_btn.clicked.connect(self.exportToMatplotlibRequested.emit)
        btns.addWidget(apply_btn)
        btns.addWidget(reset_btn)
        btns.addWidget(reload_btn)
        layout.addLayout(btns)
        layout.addWidget(export_btn)
        #export_btn.setMinimumWidth(0)
        #export_btn.setMaximumWidth(16777215)
        main_widget.setLayout(layout)
        self.setWidget(main_widget)

    def apply(self):
        params = {
            'title': self.title_edit.text().strip(),
            'xlabel': self.xlabel_edit.text().strip(),
            'ylabel': self.ylabel_edit.text().strip(),
            'xlim': (self.xlim_min.text().strip(), self.xlim_max.text().strip()),
            'ylim': (self.ylim_min.text().strip(), self.ylim_max.text().strip()),
            'grid': self.grid_check.isChecked(),
            'legend': self.legend_check.isChecked(),
            'xticks': self.xticks_edit.text().strip(),
            'yticks': self.yticks_edit.text().strip(),
        }
        self.paramsSelected.emit(params)

    def reset(self):
        self.requestResetPlot.emit()

    def reload(self):
        self.requestUpdateParams.emit()

    def focusInEvent(self, event):
        self.requestUpdateParams.emit()
        super().focusInEvent(event)


    def update_fields_from_params(self, params):
        self.title_edit.setText(params.get('title', ''))
        self.xlabel_edit.setText(params.get('xlabel', ''))
        self.ylabel_edit.setText(params.get('ylabel', ''))
        xlim = params.get('xlim', (None, None))
        if xlim and len(xlim) == 2:
            if not self.xlim_min.text():
                self.xlim_min.setPlaceholderText(str(xlim[0]) if xlim[0] is not None else '')
            if not self.xlim_max.text():
                self.xlim_max.setPlaceholderText(str(xlim[1]) if xlim[1] is not None else '')
        else:
            self.xlim_min.setPlaceholderText('X min')
            self.xlim_max.setPlaceholderText('X max')
        ylim = params.get('ylim', (None, None))
        if ylim and len(ylim) == 2:
            if not self.ylim_min.text():
                self.ylim_min.setPlaceholderText(str(ylim[0]) if ylim[0] is not None else '')
            if not self.ylim_max.text():
                self.ylim_max.setPlaceholderText(str(ylim[1]) if ylim[1] is not None else '')
        else:
            self.ylim_min.setPlaceholderText('Y min')
            self.ylim_max.setPlaceholderText('Y max')
        self.grid_check.setChecked(params.get('grid', False))
        self.legend_check.setChecked(params.get('legend', False))
        if not self.xticks_edit.text():
            self.xticks_edit.setPlaceholderText(params.get('xticks', ''))
        if not self.yticks_edit.text():
            self.yticks_edit.setPlaceholderText(params.get('yticks', '')) 