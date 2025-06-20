import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from gui.mpl_canvas import MplCanvas
from gui.plot_dialog import PlotParamDialog
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel, QTabWidget, QAction, QFileDialog, QMenuBar, QListWidget, QListWidgetItem, QMessageBox, QDockWidget, QLabel, QSizePolicy, QPushButton, QInputDialog, QMenu)
from PyQt5.QtCore import Qt
import os
from DataManagement.data_reader import read_data_file
import pandas as pd
from gui.param_widget import ParamWidget
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np
import json
from gui.line_list_widget import LineListWidget
from logger import get_logger
import logging
from localvars import RAW_DATA_DIR, PREPROCESSED_DATA_DIR, POSTPROCESSED_DATA_DIR, PLOTS_DIR, DEFAULT_PLOT_CONFIG, DEFAULT_PLOT_SAVE, PROCESSING_MODULES_DIR
from gui.processing_dialog import ProcessingDialog

logger = get_logger(__name__)

def prepare_plot_data(df, params, logger=None):
    """
    Given a DataFrame and params dict, return processed x, y arrays for plotting.
    Handles calculation fields, min/max masks, and custom mask expressions.
    """
    if 'x' not in params or 'y' not in params:
        raise ValueError("x and y must be specified in params")
    x = df[params['x']]
    y = df[params['y']]
    if x is None or y is None:
        raise ValueError("x and y must be valid columns in the DataFrame")
    # Calculation for x
    if 'calc_x' in params:
        np_env = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
        local_env = {'x': x, 'y': y}
        local_env.update(np_env)
        try:
            x = eval(params['calc_x'], {"__builtins__": {}}, local_env)
        except Exception as e:
            if logger:
                logger.error(f"X calculation error: {params['calc_x']}: {e}")
    # Calculation for y
    if 'calc_y' in params:
        np_env = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
        local_env = {'x': x, 'y': y}
        local_env.update(np_env)
        try:
            y = eval(params['calc_y'], {"__builtins__": {}}, local_env)
        except Exception as e:
            if logger:
                logger.error(f"Y calculation error: {params['calc_y']}: {e}")
    mask = np.ones(len(x), dtype=bool)
    if 'minx' in params:
        mask &= x >= float(params['minx'])
    if 'maxx' in params:
        mask &= x <= float(params['maxx'])
    if 'miny' in params:
        mask &= y >= float(params['miny'])
    if 'maxy' in params:
        mask &= y <= float(params['maxy'])
    # Custom mask expressions
    if 'mask_exprs' in params:
        np_env = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
        local_env = {'x': x, 'y': y}
        local_env.update(np_env)
        for expr in params['mask_exprs']:
            try:
                mask_expr = eval(expr, {"__builtins__": {}}, local_env)
                mask &= mask_expr
            except Exception as e:
                if logger:
                    logger.error(f"Mask expression error: {expr}: {e}")
    x = x[mask]
    y = y[mask]
    return x, y

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.verbosity = 'DEBUG'  # Can be set to INFO, WARNING, etc.
        logger.setLevel(getattr(logging, self.verbosity, logging.DEBUG))
        logger.debug('MainWindow initialized with verbosity %s', self.verbosity)
        self.setWindowTitle("Corbino Analysis GUI")
        self.setGeometry(100, 100, 1200, 800)
        
        self.statusBar = self.statusBar()

        self._create_menubar()

        # Tabs for file browsers
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)

        # Raw Data tab
        self.raw_model = QFileSystemModel()
        if not os.path.exists(RAW_DATA_DIR):
            os.makedirs(RAW_DATA_DIR)
        self.raw_model.setRootPath(RAW_DATA_DIR)
        self.raw_tree = QTreeView()
        self.raw_tree.setModel(self.raw_model)
        self.raw_tree.setRootIndex(self.raw_model.index(RAW_DATA_DIR))
        self.raw_tree.setColumnWidth(0, 250)
        self.raw_tree.setHeaderHidden(True)
        self.raw_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.tabs.addTab(self._make_tab_widget(self.raw_tree, "Raw Data"), "Raw Data")

        # Preprocessed Data tab (inserted between Raw and Postprocessed)
        if not os.path.exists(PREPROCESSED_DATA_DIR):
            os.makedirs(PREPROCESSED_DATA_DIR)
        self.pre_model = QFileSystemModel()
        self.pre_model.setRootPath(PREPROCESSED_DATA_DIR)
        self.pre_tree = QTreeView()
        self.pre_tree.setModel(self.pre_model)
        self.pre_tree.setRootIndex(self.pre_model.index(PREPROCESSED_DATA_DIR))
        self.pre_tree.setColumnWidth(0, 250)
        self.pre_tree.setHeaderHidden(True)
        self.pre_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.tabs.insertTab(1, self._make_tab_widget(self.pre_tree, "Preprocessed Data"), "Preprocessed Data")

        # Postprocessed Data tab
        if not os.path.exists(POSTPROCESSED_DATA_DIR):
            os.makedirs(POSTPROCESSED_DATA_DIR)
        self.post_model = QFileSystemModel()
        self.post_model.setRootPath(POSTPROCESSED_DATA_DIR)
        self.post_tree = QTreeView()
        self.post_tree.setModel(self.post_model)
        self.post_tree.setRootIndex(self.post_model.index(POSTPROCESSED_DATA_DIR))
        self.post_tree.setColumnWidth(0, 250)
        self.post_tree.setHeaderHidden(True)
        self.post_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.tabs.addTab(self._make_tab_widget(self.post_tree, "Postprocessed Data"), "Postprocessed Data")

        # Data Browser Dock
        self.data_browser_dock = QDockWidget("Data Browser", self)
        self.data_browser_dock.setWidget(self.tabs)
        self.data_browser_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.data_browser_dock)

        # Matplotlib plot area dock
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.plot_widget = QWidget()
        plot_layout = QVBoxLayout()
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        self.plot_widget.setLayout(plot_layout)
        self.plot_dock = QDockWidget("Plot Area", self)
        self.plot_dock.setWidget(self.plot_widget)
        self.plot_dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.addDockWidget(Qt.RightDockWidgetArea, self.plot_dock)

        # Plotted lines list dock
        self.line_list_widget = LineListWidget()
        #self.line_list_widget.setMaximumHeight(120) want to resize
        self.line_list_widget.showHideToggled.connect(self.toggle_line_visibility)
        self.line_list_widget.removeRequested.connect(self.remove_plot_line)
        self.line_list_widget.editRequested.connect(self.edit_line_params)
        #self.line_list_widget.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.lines_dock = QDockWidget("Plotted Lines", self)
        self.lines_dock.setWidget(self.line_list_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.lines_dock)

        # Parameter controls widget (already dockable)
        self.param_widget = ParamWidget(current_params=None)
        self.addDockWidget(Qt.RightDockWidgetArea, self.param_widget)
        self.param_widget.paramsSelected.connect(self.apply_global_plot_params)
        self.param_widget.requestUpdateParams.connect(self.update_param_widget_fields_from_plot)
        self.param_widget.requestResetPlot.connect(self.reset_plot_and_params)
        self.param_widget.exportToMatplotlibRequested.connect(self.export_to_matplotlib)
        # Tabify Plot Area and Plot Options by default
        self.tabifyDockWidget(self.plot_dock, self.param_widget)
        self.plot_dock.raise_()

        # Store plot info
        self.plotted_lines = []  # List of dicts: {file, params, line}

        # Connect file tree double-clicks
        self.raw_tree.doubleClicked.connect(lambda idx: self.handle_file_double_click(idx, 'raw'))
        self.post_tree.doubleClicked.connect(lambda idx: self.handle_file_double_click(idx, 'post'))
        self.pre_tree.doubleClicked.connect(lambda idx: self.handle_file_double_click(idx, 'pre'))

        self.global_params = {}

        self._setup_file_tree_context_menu()

    def _create_menubar(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        save_plot_action = QAction("Save Plot", self)
        save_plot_action.triggered.connect(self.save_plot)
        file_menu.addAction(save_plot_action)

        refresh_plot_action = QAction("Refresh Plot", self)
        refresh_plot_action.triggered.connect(self.reset_plot_and_params)
        file_menu.addAction(refresh_plot_action)

        # Add more file actions as needed

        # Edit menu (placeholder)
        edit_menu = menubar.addMenu("Edit")
        # Add edit actions as needed

        # Add File menu item for export
        export_action = QAction("Open in Matplotlib Window", self)
        export_action.triggered.connect(self.export_to_matplotlib)
        file_menu.addAction(export_action)

        # Add Export/Import Plot Config actions
        export_cfg_action = QAction("Export Plot Configuration", self)
        export_cfg_action.triggered.connect(self.export_plot_config)
        file_menu.addAction(export_cfg_action)
        import_cfg_action = QAction("Import Plot Configuration", self)
        import_cfg_action.triggered.connect(self.import_plot_config)
        file_menu.addAction(import_cfg_action)
        append_cfg_action = QAction("Append Plot Configuration", self)
        append_cfg_action.triggered.connect(self.append_plot_config)
        file_menu.addAction(append_cfg_action)

    def save_plot(self):
        options = QFileDialog.Options()
        # Ensure plots directory exists
        if not os.path.exists(PLOTS_DIR):
            os.makedirs(PLOTS_DIR)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot As",
            DEFAULT_PLOT_SAVE,
            "PDF Files (*.pdf);;PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)",
            options=options
        )
        if file_path:
            self.canvas.figure.savefig(file_path)

    def _make_tab_widget(self, tree, label):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(tree)
        widget.setLayout(layout)
        return widget

    def handle_file_double_click(self, index, tree_type):
        if tree_type == 'raw':
            model = self.raw_model
        elif tree_type == 'pre':
            model = self.pre_model
        elif tree_type == 'post':
            model = self.post_model
        else:
            logging.error(f"Invalid tree type: {tree_type}")
            return
        file_path = model.filePath(index)
        if os.path.isdir(file_path):
            return
        try:
            df, comments, meta, ftype = read_data_file(file_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not read file:\n{file_path}\n{e}")
            return
        columns = list(df.columns)
        self._last_file_info = {'comments': comments, 'meta': meta, 'filetype': ftype, 'file_path': file_path, 'df': df}
        dialog = PlotParamDialog(columns, parent=self, comments=comments)
        dialog.paramsSelected.connect(lambda params, fp=file_path, d=df: self.add_plot_line(fp, d, params, comments))
        dialog.exec_()

    def add_plot_line(self, file_path, df, params, comments):
        logger.debug(f"Adding plot line for file: {file_path}, params: {params}")
        self.set_status_message("Adding plot line...")
        try:
            x, y = prepare_plot_data(df, params, logger)
        except Exception as e:
            logger.error(f"Error preparing plot data for file: {file_path}, params: {params}, error: {e}")
            QMessageBox.warning(self, "Error", f"Could not prepare plot data for file:\n{file_path}\n{e}")
            return
        if 'legend' in params:
            label = params['legend']
        else:
            label = os.path.basename(file_path)
        plot_kwargs = {}
        if 'color' in params:
            plot_kwargs['color'] = params['color']
        if 'linestyle' in params:
            plot_kwargs['linestyle'] = params['linestyle']
        if 'marker' in params:
            plot_kwargs['marker'] = params['marker']
        
        line, = self.canvas.axes.plot(x, y, label=label, **plot_kwargs)
        self.canvas.set_line_style_and_color(line, params)
        self.canvas.apply_plot_params(self.global_params) # Reapply global params
        self.canvas.figure.tight_layout()
        self.canvas.draw()
        line_info = {'file': file_path, 'params': params, 'line': line, 'comments': comments}
        self.plotted_lines.append(line_info)
        self.line_list_widget.add_line(label, visible=True)
        logger.info(f"Plot line added: {label}")
        self.clear_status_message()

    def edit_line_params(self, idx):
        logger.debug(f"Editing line params idx={idx}")
        if 0 <= idx < len(self.plotted_lines):
            line_info = self.plotted_lines[idx]
            file_path = line_info['file']
            params = line_info['params']
            comments = line_info.get('comments', [])
            try:
                df, _, _, _ = read_data_file(file_path)
            except Exception as e:
                logger.error(f"Could not read file {file_path}: {e}")
                QMessageBox.warning(self, "Error", f"Could not read file:\n{file_path}\n{e}")
                return
            columns = list(df.columns)
            dialog = PlotParamDialog(columns, current_params=params, parent=self, comments=comments)
            dialog.paramsSelected.connect(lambda new_params, fp=file_path, d=df, idx=idx: self.update_plot_line(fp, d, new_params, idx))
            dialog.exec_()

    def update_plot_line(self, file_path, df, params, idx):
        logger.debug(f"Updating plot line idx={idx}, file={file_path}, params={params}")
        self.set_status_message("Updating plot line...")
        try:
            x, y = prepare_plot_data(df, params, logger)
        except Exception as e:
            logger.error(f"Error preparing updated plot data for file: {file_path}, params: {params}, error: {e}")
            QMessageBox.warning(self, "Error", f"Could not prepare updated plot data for file:\n{file_path}\n{e}")
            return
        line = self.plotted_lines[idx]['line']
        line.set_xdata(x)
        line.set_ydata(y)
        if 'legend' in params:
            line.set_label(params['legend'])
        else:
            line.set_label(f"{params['y']} vs {params['x']}")
        self.plotted_lines[idx]['params'] = params
        self.plotted_lines[idx]['line'] = line
        # Update label in custom widget
        
        self.canvas.set_line_style_and_color(line, params)
        # TODO: make this better?
        self.line_list_widget.list_widget.itemWidget(self.line_list_widget.list_widget.item(idx)).layout().itemAt(1).widget().setText(line.get_label())
        self.canvas.axes.relim()
        self.canvas.apply_plot_params(self.global_params)
        self.canvas.figure.tight_layout()
        self.canvas.draw()
        logger.info(f"Plot line updated at idx={idx}")
        self.clear_status_message()
        

    def refresh_plot(self):
        # This method is now handled by apply_plot_params
        pass

    def apply_global_plot_params(self, params):
        self.set_status_message("Applying global plot parameters...")
        self.global_params = params
        self.canvas.apply_plot_params(params)
        self.canvas.figure.tight_layout()
        self.canvas.draw()
        self.plot_dock.raise_() # Show plot now
        self.clear_status_message()

    def update_param_widget_fields_from_plot(self):
        params = self.canvas.get_plot_params()
        self.param_widget.update_fields_from_params(params)

    def redraw_plot(self):
        logger.debug("Redrawing plot with current plotted_lines.")
        self.canvas.axes.clear()
        for line_info in self.plotted_lines:
            try:
                df, _, _, _ = read_data_file(line_info['file'])
            except Exception as e:
                logger.error(f"Error reading file {line_info['file']}: {e}")
                continue
            params = line_info['params']
            try:
                x, y = prepare_plot_data(df, params, logger)
            except Exception as e:
                logger.error(f"Error redrawing plot data for file: {line_info['file']}, params: {params}, error: {e}")
                QMessageBox.warning(self, "Error", f"Could not redraw plot data for file:\n{line_info['file']}\n{e}")
                continue
            label = params.get('legend', line_info['file'])
            line, = self.canvas.axes.plot(x, y, label=label)
            line_info['line'] = line
            self.canvas.set_line_style_and_color(line, params)
        logger.info("Plot redrawn.")

    def reset_plot_and_params(self):
        logger.debug("Resetting plot and parameters...")
        self.set_status_message("Resetting plot and parameters...")
        self.redraw_plot()
        self.canvas.apply_plot_params({'legend': True})
        self.canvas.figure.tight_layout()
        self.canvas.draw()
        self.param_widget.title_edit.clear()
        self.param_widget.xlabel_edit.clear()
        self.param_widget.ylabel_edit.clear()
        self.param_widget.xlim_min.clear()
        self.param_widget.xlim_max.clear()
        self.param_widget.ylim_min.clear()
        self.param_widget.ylim_max.clear()
        self.param_widget.grid_check.setChecked(False)
        self.param_widget.legend_check.setChecked(True)
        self.param_widget.xticks_edit.clear()
        self.param_widget.yticks_edit.clear()
        self.update_param_widget_fields_from_plot()
        self.plot_dock.raise_()
        self.clear_status_message()
        logger.info("Plot and parameters reset.")

    def export_to_matplotlib(self):
        self.set_status_message("Exporting plot to matplotlib window...")

        w, ok1 = QInputDialog.getDouble(self, "Figure Width", "Width (inches):", 8.0, 1.0, 30.0, 1)
        h, ok2 = QInputDialog.getDouble(self, "Figure Height", "Height (inches):", 6.0, 1.0, 30.0, 1)
        if not (ok1 and ok2):
            return
        fig, ax = plt.subplots(figsize=(w, h))
        for line_info in self.plotted_lines:
            df, _, _, _ = read_data_file(line_info['file'])
            params = line_info['params']
            try:
                x, y = prepare_plot_data(df, params, logger)
            except Exception as e:
                logger.error(f"Error preparing for export plot data for file: {line_info['file']}, params: {params}, error: {e}")
                QMessageBox.warning(self, "Error", f"Could not prepare for export plot data for file:\n{line_info['file']}\n{e}")
                continue
            label = params.get('legend', line_info['file'])
            plot_kwargs = {}
            if 'color' in params:
                plot_kwargs['color'] = params['color']
            if 'linestyle' in params:
                plot_kwargs['linestyle'] = params['linestyle']
            if 'marker' in params:
                plot_kwargs['marker'] = params['marker']
            ax.plot(x, y, label=label, **plot_kwargs)
        # Apply global params
        global_params = self.canvas.get_plot_params()
        ax.set_title(global_params.get('title', ''))
        ax.set_xlabel(global_params.get('xlabel', ''))
        ax.set_ylabel(global_params.get('ylabel', ''))
        xlim = global_params.get('xlim', (None, None))
        if xlim and xlim[0] is not None and xlim[1] is not None:
            ax.set_xlim(xlim)
        ylim = global_params.get('ylim', (None, None))
        if ylim and ylim[0] is not None and ylim[1] is not None:
            ax.set_ylim(ylim)
        if global_params.get('grid', False):
            ax.grid(True)
        if global_params.get('legend', True):
            ax.legend()
        xticks = global_params.get('xticks', '')
        if xticks:
            try:
                xtick_vals = [float(x.strip()) for x in xticks.split(',') if x.strip()]
                ax.set_xticks(xtick_vals)
            except Exception:
                pass
        yticks = global_params.get('yticks', '')
        if yticks:
            try:
                ytick_vals = [float(y.strip()) for y in yticks.split(',') if y.strip()]
                ax.set_yticks(ytick_vals)
            except Exception:
                pass
        fig.tight_layout()
        plt.show()
        self.clear_status_message()

    def export_plot_config(self):
        self.set_status_message("Exporting plot configuration...")
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Plot Configuration", DEFAULT_PLOT_CONFIG, "JSON Files (*.json)")
        if not file_path:
            self.set_status_message("")
            return
        # Prepare config dict
        config = {
            'plotted_lines': [
                {
                    'file': line['file'],
                    'params': line['params'],
                    'comments': line.get('comments', [])
                } for line in self.plotted_lines
            ],
            'global_params': self.global_params
        }
        try:
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            self.set_status_message(f"Exported plot configuration to {file_path}", 5000)
        except Exception as e:
            self.set_status_message(f"Export failed: {e}", 5000)


    def __add_plot_line_from_config(self, line_info):
        file = line_info['file']
        params = line_info['params']
        comments = line_info.get('comments', [])
        try:
            df, _, _, _ = read_data_file(file)
        except Exception as e:
            logger.error(f"Could not read file {file}: {e}")
            return
        self.add_plot_line(file, df, params, comments)

    def import_plot_config(self):
        self.set_status_message("Importing plot configuration...")
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Plot Configuration", DEFAULT_PLOT_CONFIG, "JSON Files (*.json)")
        if not file_path:
            self.set_status_message("")
            return
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            # Clear current plot
            self.canvas.axes.clear()
            self.line_list_widget.clear()
            self.plotted_lines = []
            # Restore lines
            for line_info in config.get('plotted_lines', []):
                self.__add_plot_line_from_config(line_info)
            # Restore global params
            global_params = config.get('global_params', {})
            self.global_params = global_params
            self.canvas.apply_plot_params(global_params)
            self.canvas.figure.tight_layout()
            self.canvas.draw()
            self.update_param_widget_fields_from_plot()
            self.set_status_message(f"Imported plot configuration from {file_path}", 5000)
        except Exception as e:
            self.set_status_message(f"Import failed: {e}", 5000)

    def append_plot_config(self):
        self.set_status_message("Appending plot configuration...")
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Append Plot Configuration", DEFAULT_PLOT_CONFIG, "JSON Files (*.json)")
        if not file_path:
            self.set_status_message("")
            return
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            # Restore lines
            for line_info in config.get('plotted_lines', []):
                self.__add_plot_line_from_config(line_info)
            # Restore global params
            global_params = config.get('global_params', {})
            self.global_params = global_params
            self.canvas.apply_plot_params(global_params)
            self.canvas.figure.tight_layout()
            self.canvas.draw()
            self.update_param_widget_fields_from_plot()
            self.set_status_message(f"Appended plot configuration from {file_path}", 5000)
        except Exception as e:
            self.set_status_message(f"Append failed: {e}", 5000)

    # TODO: Add option to use numpy.loadtxt instead of pandas.read_csv for data reading

    def set_status_message(self, msg, timeout=0):
        self.statusBar.showMessage(msg, timeout)
        QApplication.processEvents()
    
    def clear_status_message(self):
        self.statusBar.clearMessage()

    def toggle_line_visibility(self, idx, visible):
        logger.debug(f"Toggling line visibility idx={idx}, visible={visible}")
        if 0 <= idx < len(self.plotted_lines):
            line = self.plotted_lines[idx]['line']
            line.set_visible(visible)
            self.canvas.draw()
            logger.info(f"Line visibility toggled idx={idx}, visible={visible}")
        else:
            logger.error(f"Error toggling line visibility: {idx} is out of range")

    def remove_plot_line(self, idx):
        logger.debug(f"Removing plot line idx={idx}")
        if 0 <= idx < len(self.plotted_lines):
            line = self.plotted_lines[idx]['line']
            try:
                line.remove()
            except Exception as e:
                logger.error(f"Error removing line: {e}")
            self.plotted_lines.pop(idx)
            self.line_list_widget.remove_line(idx)
            self.redraw_plot()
            self.canvas.apply_plot_params(self.global_params)
            self.canvas.figure.tight_layout()
            self.canvas.draw()
            logger.info(f"Plot line removed idx={idx}")
        else:
            logger.error(f"Error removing line: {idx} is out of range")

    #def _on_item_double_clicked(self, item):
    #    idx = self.line_list_widget.list_widget.row(item)
    #    self.edit_line_params(idx)

    def _setup_file_tree_context_menu(self):
        self.raw_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.raw_tree.customContextMenuRequested.connect(lambda pos: self._show_file_context_menu(self.raw_tree, pos, 'raw'))
        self.post_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.post_tree.customContextMenuRequested.connect(lambda pos: self._show_file_context_menu(self.post_tree, pos, 'post'))
        self.pre_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pre_tree.customContextMenuRequested.connect(lambda pos: self._show_file_context_menu(self.pre_tree, pos, 'pre'))

    def _show_file_context_menu(self, tree, pos, tree_type):
        index = tree.indexAt(pos)
        if not index.isValid():
            return
        model = self.raw_model if tree_type == 'raw' else self.post_model
        if tree_type == 'raw':
            model = self.raw_model
        elif tree_type == 'post':
            model = self.post_model
        elif tree_type == 'pre':
            model = self.pre_model
        else:
            logging.error(f"Invalid tree type: {tree_type}")
            return
        file_path = model.filePath(index)
        if os.path.isdir(file_path):
            return
        menu = QMenu()
        preprocess_action = QAction('Preprocess with...', self)
        postprocess_action = QAction('Postprocess with...', self)
        preprocess_action.triggered.connect(lambda: self._run_processing_dialog(file_path, 'pre'))
        postprocess_action.triggered.connect(lambda: self._run_processing_dialog(file_path, 'post'))
        menu.addAction(preprocess_action)
        menu.addAction(postprocess_action)
        menu.exec_(tree.viewport().mapToGlobal(pos))

    def _run_processing_dialog(self, file_path, mode):
        # Load columns for dropdowns using data_reader
        self.set_status_message(f"Waiting on processing dialog for {file_path} in {mode} mode...")
        columns = []
        df = None
        try:
            df, _, _, _ = read_data_file(file_path)
            columns = list(df.columns)
        except Exception as e:
            logger.warning(f'Could not read columns from {file_path}: {e}')
        try:
            dialog = ProcessingDialog(file_path, module_type=mode, data_columns=columns, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                module_name, module_cls, params = dialog.get_selected_module()
                if module_name is None:
                    logger.warning(f"No module selected for {file_path} in {mode} mode")
                    raise Exception("No module selected")
                logger.info(f"Processing {file_path} with {module_name} in {mode} mode...")
                self.set_status_message(f"Processing {file_path} with {module_name} in {mode} mode...")
                # Determine output dir based on mode
                if mode == 'pre':
                    output_dir = PREPROCESSED_DATA_DIR
                else:
                    output_dir = POSTPROCESSED_DATA_DIR
                module = module_cls(file_path, output_dir, params, df)
                try:
                    module.load()
                    module.process()
                    module.save()
                    QMessageBox.information(self, "Processing Complete", f"Processing complete. Output saved to {output_dir}")
                except Exception as e:
                    QMessageBox.warning(self, "Processing Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Dialog Error", str(e))
            #raise e

        self.clear_status_message()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 