import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from gui.mpl_canvas import MplCanvas
from gui.plot_dialog import PlotParamDialog, CalcPlotParamDialog
from PyQt5.QtWidgets import (QStyle, QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel, QTabWidget, QAction, QFileDialog, QMenuBar, QListWidget, QListWidgetItem, QMessageBox, QDockWidget, QLabel, QSizePolicy, QPushButton, QInputDialog, QMenu, QActionGroup, QToolBar)
from PyQt5.QtCore import Qt, pyqtSignal
import os
from DataManagement.data_reader import read_data_file
import pandas as pd
from gui.param_widget import ParamWidget
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtGui import QIcon # Make sure QIcon is imported

class NavigationToolbar(NavigationToolbar2QT):

    artists_changed = pyqtSignal()
    toolitems = [
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan',
         'Left button pans, Right button zooms\n'
         'x/y fixes axis, CTRL fixes aspect',
         'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis', 'zoom_to_rect', 'zoom'),
        ('Add Text', 'Add Text', 'text', 'add_text'),
        ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
    ]

    def __init__(self, canvas, parent, coordinates=True):
        super().__init__(canvas, parent, coordinates)

        # --- Add Custom Actions ---
        self.addSeparator()

        # Create an exclusive action group for interaction modes
        action_group = QActionGroup(self)
        action_group.setExclusive(True)
        # Create 'Add Text' action
        text_icon = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)  # Using a stock icon
        text_action = QAction(text_icon, "Add Text", self, checkable=True)
        text_action.setData('text')
        action_group.addAction(text_action)
        self.addAction(text_action)

        #self._action['text'].

        action_group.triggered.connect(self._on_interaction_mode_triggered)

    def _on_interaction_mode_triggered(self, action):
        """"""
        pass

    def add_text(self):
        pass