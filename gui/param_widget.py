from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QPushButton, QHBoxLayout, QLabel)
from PyQt5.QtCore import pyqtSignal
from logger import get_logger

logger = get_logger(__name__)

class ParamWidget(QWidget):
    paramsSelected = pyqtSignal(dict)
    requestUpdateParams = pyqtSignal()
    requestResetPlot = pyqtSignal()
    exportToMatplotlibRequested = pyqtSignal()

    def __init__(self, current_params=None, parent=None):
        super().__init__(parent)
        logger.debug('ParamWidget initialized')
        self.current_params = current_params or {}
        self._init_ui()

    def _init_ui(self):
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
        self.setLayout(layout)
    
    def export_params(self):
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
        logger.debug(f'Exported params: {params}')
        return params

    def apply(self):
        params = self.export_params()
        logger.info('Params applied')
        self.paramsSelected.emit(params)

    def reset(self):
        logger.info('Params reset requested')
        self.requestResetPlot.emit()

    def reload(self):
        logger.info('Params reload requested')
        self.requestUpdateParams.emit()

    def focusInEvent(self, event):
        logger.debug('ParamWidget gained focus')
        self.requestUpdateParams.emit()
        super().focusInEvent(event)

    def update_fields_from_params(self, params):
        logger.debug(f'Updating fields from params: {params}')
        self.title_edit.setText(params.get('title', ''))
        self.xlabel_edit.setText(params.get('xlabel', ''))
        self.ylabel_edit.setText(params.get('ylabel', ''))
        xlim = params.get('xlim', (None, None))
        xlim_custom = params.get('xlim_custom', False)
        if xlim and len(xlim) == 2:
            if xlim_custom:
                self.xlim_min.setText(str(xlim[0]) if xlim[0] is not None else '')
                self.xlim_max.setText(str(xlim[1]) if xlim[1] is not None else '')
            else:
                self.xlim_min.clear()
                self.xlim_max.clear()
                self.xlim_min.setPlaceholderText(str(xlim[0]) if xlim[0] is not None else 'X min')
                self.xlim_max.setPlaceholderText(str(xlim[1]) if xlim[1] is not None else 'X max')
        else:
            self.xlim_min.clear()
            self.xlim_max.clear()
            self.xlim_min.setPlaceholderText('X min')
            self.xlim_max.setPlaceholderText('X max')
        ylim = params.get('ylim', (None, None))
        ylim_custom = params.get('ylim_custom', False)
        if ylim and len(ylim) == 2:
            if ylim_custom:
                self.ylim_min.setText(str(ylim[0]) if ylim[0] is not None else '')
                self.ylim_max.setText(str(ylim[1]) if ylim[1] is not None else '')
            else:
                self.ylim_min.clear()
                self.ylim_max.clear()
                self.ylim_min.setPlaceholderText(str(ylim[0]) if ylim[0] is not None else 'Y min')
                self.ylim_max.setPlaceholderText(str(ylim[1]) if ylim[1] is not None else 'Y max')
        else:
            self.ylim_min.clear()
            self.ylim_max.clear()
            self.ylim_min.setPlaceholderText('Y min')
            self.ylim_max.setPlaceholderText('Y max')
        self.grid_check.setChecked(params.get('grid', False))
        self.legend_check.setChecked(params.get('legend', False))
        if not self.xticks_edit.text():
            self.xticks_edit.setPlaceholderText(params.get('xticks', ''))
        if not self.yticks_edit.text():
            self.yticks_edit.setPlaceholderText(params.get('yticks', ''))
        logger.info('Fields updated from params') 