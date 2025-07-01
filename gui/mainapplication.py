import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from gui.mpl_canvas import MplCanvas
from gui.plot_dialog import PlotParamDialog, CalcPlotParamDialog
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
from localvars import RAW_DATA_DIR, PREPROCESSED_DATA_DIR, POSTPROCESSED_DATA_DIR, PLOTS_DIR, DEFAULT_PLOT_CONFIG, DEFAULT_PLOT_SAVE, REREAD_DATAFILE_ON_EDIT, PROCESSING_MODULES_DIR
from gui.mpl_rcparams_widget import MplRcParamsWidget
from gui.processing_dialog import ProcessingDialog
from gui.plot_module_widget import PlotModuleWidget

logger = get_logger(__name__)

def _perform_plot_calcs(x, y, params, logger=None):
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

def _prepare_simple_plot_data(df, params, logger=None):
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

    return _perform_plot_calcs(x, y, params, logger=logger)
    #return x, y

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

def _prepare_multi_plot_data(df, params, logger=None):
    """
    Prepares data by evaluating expressions with user-defined variables.
    """
    definitions = params.get('definitions', {})
    x_expr = params.get('x_expression')
    y_expr = params.get('y_expression')

    if not all([definitions, x_expr, y_expr]):
        raise ValueError("Multi-column plot is missing definitions or expressions.")

    # Build the local environment for eval()
    local_env = {}
    for var_name, col_name in definitions.items():
        if col_name in df.columns:
            local_env[var_name] = df[col_name]
        else:
            raise ValueError(f"Column '{col_name}' defined for variable '{var_name}' not found in data.")

    # Add numpy functions for convenience
    np_env = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
    local_env.update(np_env)

    try:
        x_data = eval(x_expr, {"__builtins__": {}}, local_env)
        logger.debug(f"Evaluated x_expression '{x_expr}' successfully.")
    except Exception as e:
        logger.error(f"Error evaluating x_expression '{x_expr}': {e}")
        raise ValueError(f"Error in X-Axis Expression: {e}")

    try:
        y_data = eval(y_expr, {"__builtins__": {}}, local_env)
        logger.debug(f"Evaluated y_expression '{y_expr}' successfully.")
    except Exception as e:
        logger.error(f"Error evaluating y_expression '{y_expr}': {e}")
        raise ValueError(f"Error in Y-Axis Expression: {e}")


    return _perform_plot_calcs(x_data, y_data, params, logger=logger)
    return x_data, y_data

def prepare_plot_data(df, params, logger=None):
    """
    Dispatcher function that calls the correct data preparation function based on 'plot_type'
    """
    if params.get('plot_type') == 'multi_column':
        return _prepare_multi_plot_data(df, params, logger)
    else:
        return _prepare_simple_plot_data(df, params, logger)


def make_dock_widget(self, widget, dock_area = Qt.AllDockWidgetAreas, title = None):
    dock = QDockWidget(title if title else widget.windowTitle(), self)
    dock.setWidget(widget)
    dock.setAllowedAreas(dock_area)
    return dock


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
        #self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        #self.toolbar = NavigationToolbar(self.canvas, self)
        self.plot_widget = QWidget()
        self.canvas = None # Will be created in next call
        self.toolbar = None # Will be created in next call
        self._add_mpl_canvas()
        """
        plot_layout = QVBoxLayout()
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        self.plot_widget.setLayout(plot_layout)
        """
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
        #self.plot_dock.raise_()

        # Plot modules widget
        self.plot_module_widget = PlotModuleWidget(parent=self)

        self.addDockWidget(Qt.RightDockWidgetArea, self.plot_module_widget)
        self.plot_module_widget.modulesChanged.connect(self.on_plot_modules_changed)

        # Tabify with parameter widget
        self.tabifyDockWidget(self.param_widget, self.plot_module_widget)

        # rcParams widget
        self.rcparams_widget = MplRcParamsWidget(parent=self)
        self.rcparams_dock = make_dock_widget(self, self.rcparams_widget, title="Plot RCParams", dock_area = Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.rcparams_dock)
        self.rcparams_widget.applyPressed.connect(self.on_rcParam_changed)

        # Tabify with plot modules widget
        self.tabifyDockWidget(self.plot_module_widget, self.rcparams_dock)

        # Raise plot area
        self.plot_dock.raise_()

        # Store plot info
        self.plotted_lines = []  # List of dicts: {file, params, line}
        self.plot_modules = []  # List of active plot module instances

        # Connect file tree double-clicks
        self.raw_tree.doubleClicked.connect(lambda idx: self.handle_file_double_click(idx, 'raw'))
        self.post_tree.doubleClicked.connect(lambda idx: self.handle_file_double_click(idx, 'post'))
        self.pre_tree.doubleClicked.connect(lambda idx: self.handle_file_double_click(idx, 'pre'))

        self.global_params = {}

        self._setup_file_tree_context_menu()

    def _add_mpl_canvas(self):
        """
        Adds/Resets the MplCanvas widget fully by deleting the old canvas and toolbar
        and creating new ones in their place. This ensures a clean slate for the plot.
        """
        logger.debug("Creating new MplCanvas and toolbar.")

        # Get the existing layout or create a new one if it doesn't exist.
        plot_layout = self.plot_widget.layout()
        if plot_layout:
            # Clear existing widgets from the layout
            while plot_layout.count():
                item = plot_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()  # Schedule old widgets for deletion
        else:
            # If no layout exists (first call), create one and set it
            plot_layout = QVBoxLayout()
            plot_layout.setContentsMargins(0, 0, 0, 0)
            plot_layout.setSpacing(0)
            self.plot_widget.setLayout(plot_layout)

        # Now, current_plot_layout is guaranteed to exist and be empty.
        # The old self.canvas and self.toolbar references are already cleared by deleteLater()
        # from the previous iteration, if any.

        # Create new MplCanvas and NavigationToolbar instances
        # Use the same dimensions as the initial setup
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Add the new toolbar and canvas to the current layout
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        logger.info("Added MplCanvas and toolbar.")

    # ... (rest of the MainWindow class)

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
            logger.error(f"Invalid tree type: {tree_type}")
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

    def handle_file_plot_math(self, file_path): # Plots math
        if os.path.isdir(file_path):
            return
        try:
            df, comments, meta, ftype = read_data_file(file_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not read file:\n{file_path}\n{e}")
            return
        columns = list(df.columns)
        self._last_file_info = {'comments': comments, 'meta': meta, 'filetype': ftype, 'file_path': file_path, 'df': df}

        dialog = CalcPlotParamDialog(columns, parent=self, comments=comments)
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

        self.canvas.update_visuals(self.global_params, self.plot_modules)
        #self.canvas.apply_plot_params(self.global_params) # Reapply global params
        #self.canvas.figure.tight_layout()
        #self.canvas.draw()
        line_info = {'file': file_path, 'df': df, 'params': params, 'line': line, 'comments': comments}
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
            if REREAD_DATAFILE_ON_EDIT:
                try:
                    df, _, _, _ = read_data_file(file_path)
                except Exception as e:
                    logger.error(f"Could not read file {file_path}: {e}")
                    QMessageBox.warning(self, "Error", f"Could not read file:\n{file_path}\n{e}")
                    return
            else:
                df = line_info['df']

            columns = list(df.columns)
            if params.get('plot_type') == 'multi_column':
                dialog = CalcPlotParamDialog(columns, parent=self, current_params=params, comments=comments)
            else:
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
            try:
                line.set_label(f"{params['y']} vs {params['x']}")
            except: # TODO: make sure the x/y are supplied via expressions
                line.set_label(f"{os.path.basename(file_path)}")
        self.plotted_lines[idx]['params'] = params
        self.plotted_lines[idx]['line'] = line
        self.plotted_lines[idx]['df'] = df # Only if rereading is enabled, otherwise makes no difference
        # Update label in custom widget
        
        self.canvas.set_line_style_and_color(line, params)
        # TODO: make this better?
        self.line_list_widget.list_widget.itemWidget(self.line_list_widget.list_widget.item(idx)).layout().itemAt(1).widget().setText(line.get_label())
        self.canvas.axes.relim()

        self.canvas.update_visuals(self.global_params, self.plot_modules)
        #self.canvas.apply_plot_params(self.global_params)
        #self.canvas.figure.tight_layout()
        #self.canvas.draw()
        logger.info(f"Plot line updated at idx={idx}")
        self.clear_status_message()
        

    def refresh_plot(self):
        # This method is now handled by apply_plot_params
        pass

    def apply_global_plot_params(self, params):
        self.set_status_message("Applying global plot parameters...")
        self.global_params = params
        self.canvas.update_visuals(self.global_params, self.plot_modules)
        #self.canvas.apply_plot_params(params)
        #self.canvas.figure.tight_layout()
        #self.canvas.draw()
        self.plot_dock.raise_() # Show plot now
        self.clear_status_message()

    def update_param_widget_fields_from_plot(self):
        params = self.canvas.get_plot_params()
        self.param_widget.update_fields_from_params(params)

    def redraw_plot(self):
        logger.debug("Redrawing plot with current plotted_lines.")
        self.canvas.axes.clear()
        for line_info in self.plotted_lines:
            df = line_info['df']
            """
            try:
                df, _, _, _ = read_data_file(line_info['file'])
            except Exception as e:
                logger.error(f"Error reading file {line_info['file']}: {e}")
                continue
            """
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
        # TODO: reset all plot modules
        # self.plot_modules.reset.emit() or something along those lines
        self.canvas.update_visuals({'legend': True}, self.plot_modules)
        #self.canvas.apply_plot_params({'legend': True})
        #self.canvas.figure.tight_layout()
        #self.canvas.draw()
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
            df = line_info['df']
            #df, _, _, _ = read_data_file(line_info['file'])
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

    def export_plot_config(self, file_path = None):
        self.set_status_message("Exporting plot configuration...")
        if not file_path: # If not supplied, we simply ask
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Plot Configuration", DEFAULT_PLOT_CONFIG, "JSON Files (*.json)")
            if not file_path:
                self.set_status_message("")
                return
        # Prepare config dict
        config = {
            'plotted_lines': [
                { # This is all we need, everything else gets created in add_plot_line()
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

        try:
            self.add_plot_line(file, df, params, comments)
        except Exception as e:
            logger.error(f"Could not add plot line for file {file}: {e}")

    def import_plot_config(self, file_path = None):
        self.set_status_message("Importing plot configuration...")
        if not file_path: # If not supplied, we simply ask
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
            self.canvas.update_visuals(self.global_params, self.plot_modules)
            #self.canvas.apply_plot_params(global_params)
            #self.canvas.figure.tight_layout()
            #self.canvas.draw()
            self.update_param_widget_fields_from_plot()
            self.set_status_message(f"Imported plot configuration from {file_path}", 5000)
        except Exception as e:
            self.set_status_message(f"Import failed: {e}", 5000)

    def append_plot_config(self, file_path = None):
        self.set_status_message("Appending plot configuration...")
        if not file_path: # If not supplied, we simply ask
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

            self.canvas.update_visuals(self.global_params, self.plot_modules)
            #self.canvas.apply_plot_params(global_params)
            #self.canvas.figure.tight_layout()
            #self.canvas.draw()
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

            self.canvas.update_visuals(self.global_params, self.plot_modules)
            #self.canvas.apply_plot_params(self.global_params)
            #self.canvas.figure.tight_layout()
            #self.canvas.draw()
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
            logger.error(f"Invalid tree type: {tree_type}")
            return
        file_path = model.filePath(index)
        if os.path.isdir(file_path):
            return
        menu = QMenu()
        # Math action
        plot_math_action = QAction('Plot with expression...', self)
        plot_math_action.triggered.connect(lambda: self.handle_file_plot_math(file_path = file_path))
        menu.addAction(plot_math_action)
        menu.addSeparator()
        # Preprocess/Postprocess actions
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
        try: # Reread if plotted because, we shouldn't assume its already loaded
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

    def reload_plot_modules(self):
        """
        This is to force a reload on all plot modules if, say, the rcParams are changed externally

        for use with updated rcparams from global table
        """
        logger.debug("Reloading plot modules...")
        self.plot_module_widget._reload_modules() # Silent reload
        modules = self.plot_module_widget.export_modules()
        for module in self.plot_modules:
            module.disable(self.canvas.axes)
        self.plot_modules = modules
        logger.debug("Plot modules reloaded.")

    def on_plot_modules_changed(self, modules):
        """Handle plot module changes"""
        reset_plot = False

        # Disable previous modules
        for module in self.plot_modules:
            reset_plot |= (module.disable(self.canvas.axes) or module.reset_plot) # In the event of a None, default to false

        # Add new modules
        self.plot_modules = modules
        logger.info(f"Plot modules changed: {[m.name for m in modules]}")
        # Run initialize functions, should any need to be initialized before plotting (i.e. when plot reset is required
        for module in modules:  # Note, initialize() will return True only when a reset is desired
            reset_plot |= (module.initialize() or module.reset_plot)  # Run possible initialize function
        # Incase a module modifies global parameters heavily and needs a reset
        if reset_plot:
            logger.info("Plot module(s) require plot reset.")
            self._add_mpl_canvas()
        # Redraw the plot to apply the new modules
        self.redraw_plot()
        self.canvas.update_visuals(self.global_params, self.plot_modules)
        self.plot_dock.raise_()

    def on_rcParam_changed(self):
        # We are reloading plot modules, so disable and initialize them
        for module in self.plot_modules:
            module.disable(self.canvas.axes)
        for module in self.plot_modules:
            module.initialize()
        self._add_mpl_canvas()
        self.redraw_plot()
        self.canvas.update_visuals(self.global_params, self.plot_modules)
        self.plot_dock.raise_()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
