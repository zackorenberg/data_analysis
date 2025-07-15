import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from gui.mpl_canvas import MplCanvas
from gui.plot_dialog import PlotParamDialog, CalcPlotParamDialog
from PyQt5.QtWidgets import (QColorDialog, QStyle, QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel, QTabWidget, QAction, QFileDialog, QMenuBar, QListWidget, QListWidgetItem, QMessageBox, QDockWidget, QLabel, QSizePolicy, QPushButton, QInputDialog, QMenu, QActionGroup, QToolBar)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor
import os
from DataManagement.data_reader import read_data_file
import pandas as pd
from gui.param_widget import ParamWidget
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib import (_api, backend_tools as tools)
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtGui import QIcon # Make sure QIcon is imported
from enum import Enum


class _Mode(str, Enum):
    NONE = ""
    PAN = "pan/zoom"
    ZOOM = "zoom rect"
    TEXT = "add text"

    def __str__(self):
        return self.value

    @property
    def _navigate_mode(self):
        return self.name if self is not _Mode.NONE else None



class NavigationToolbar(NavigationToolbar2QT):
    # Signals
    artists_changed = pyqtSignal()
    export_requested = pyqtSignal()

    # Toolitems with overridden icons
    toolitems = [
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'arrow-left', 'back'),
        ('Forward', 'Forward to next view', 'arrow-right', 'forward'),
        (None, None, None, None),
        ('Pan',
         'Left button pans, Right button zooms\n'
         'x/y fixes axis, CTRL fixes aspect',
         'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis', 'zoom', 'zoom'),
        ('Subplots', 'Configure subplots', 'sliders-horizontal', 'configure_subplots'),
        ("Customize", "Edit axis, curve and image parameters",
        "figure", "edit_parameters"),
        (None, None, None, None),
        ('Add Text', 'Add Text', 'text', 'text'),
        ('Color', 'Change Color', 'paint-palette', 'set_color'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'save', 'save_figure'),
        ('Export', 'Export the figure parameters', 'export', 'export_figure'),
    ]


    def __init__(self, canvas, parent, coordinates=True):

        self.icons_path = os.path.join('gui','resources','icons') # TODO: move to localvars
        self.parent = parent
        self._last_cursor = None
        super().__init__(canvas, parent, coordinates)

        """
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
        """
        self._current_color = QColor(0,0,0)

        self._toggleable_callbacks = [s.name.lower() for s in _Mode if s != 'NONE']

        self._icons = {}
        for name, desc, image_file, callback in self.toolitems:
            if image_file:
                self._icons[callback] = self._icon(image_file)
                self._actions[callback].setIcon(self._icons[callback])

            print(callback, self._toggleable_callbacks)
            if callback in self._toggleable_callbacks:
                self._actions[callback].setCheckable(True)
                print(callback)


    def _icon(self, name):
        path = os.path.join(self.icons_path, f"{name}.svg")
        if not os.path.exists(path):
            print(name)
        return QIcon(path)


    def _on_interaction_mode_triggered(self, action):
        """"""
        pass

    def pan(self):
        super().pan()
        self._update_buttons_checked()

    def zoom(self):
        super().zoom()
        self._update_buttons_checked()

    def text(self):
        if not self.canvas.widgetlock.available(self):
            self.set_message("text unavailable")
            return
        if self.mode == _Mode.TEXT:
            self.mode = _Mode.NONE
            self.canvas.widgetlock.release(self)
        else:
            self.mode = _Mode.TEXT
            self.canvas.widgetlock(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self.mode._navigate_mode)
        self._update_buttons_checked()

    def export_figure(self):
        pass

    def set_color(self):
        color = QColorDialog.getColor(self._current_color, self, "Choose Color")
        if color.isValid():
            self._current_color = color
            pixmap = self._icons['set_color'].pixmap(516)
            mask = pixmap.createMaskFromColor(QColor("transparent"), Qt.MaskInColor)
            pixmap.fill(color) # TODO CHANGE
            pixmap.setMask(mask)
            icon = QIcon(pixmap)
            self._icons['set_color'] = icon
            self._actions['set_color'].setIcon(icon)

    def _update_buttons_checked(self):
        # sync button checkstates to match active mode
        for callback in self._toggleable_callbacks:
            if callback in self._actions:
                self._actions[callback].setChecked(self.mode.name.lower() == callback)

    def _update_cursor(self, event):
        """
        Update the cursor after a mouse move event or a tool (de)activation.
        """
        if self.mode and event.inaxes and event.inaxes.get_navigate():
            if (self.mode == _Mode.ZOOM and self._last_cursor != tools.Cursors.SELECT_REGION):
                self._last_cursor = tools.Cursors.SELECT_REGION
            elif (self.mode == _Mode.PAN and self._last_cursor != tools.Cursors.MOVE):
                self._last_cursor = tools.Cursors.MOVE
        elif self._last_cursor != tools.Cursors.POINTER:
            self._last_cursor = tools.Cursors.POINTER

        self.canvas.set_cursor(self._last_cursor)

    def mouse_move(self, event):
        self._update_cursor(event)
        self.set_message(self._mouse_event_to_message(event))


'''
ToolToggleBase which needs to be refactored to NavigationToolbar2QT

class AddTextTool(ToolToggleBase):
    """A Matplotlib Tool to add text to the plot canvas."""
    description = 'Add text to the figure'
    default_keymap = 't'  # Optional keyboard shortcut

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cid = None

    def enable(self, event=None):
        """
        This method is called when the tool is activated.
        It connects the 'button_press_event' to our handler.
        """
        self.cid = self.figure.canvas.mpl_connect(
            'button_press_event', self._on_press)

    def disable(self, event=None):
        """
        This method is called when the tool is deactivated.
        It disconnects the event handler.
        """
        if self.cid:
            self.figure.canvas.mpl_disconnect(self.cid)
            self.cid = None

    def _on_press(self, event):
        """
        Handles the button press event on the canvas. It prompts the user
        for text and adds it to the plot at the click location.
        """
        # Ignore clicks outside of an axes object
        if not event.inaxes:
            return

        # The tool needs a reference to a QWidget to parent the dialog.
        # We get it from the canvas.
        main_window = self.figure.canvas.parent()
        text, ok = QInputDialog.getText(main_window, "Add Text", "Enter text:")

        if ok and text:
            # Add the text artist to the plot
            artist = event.inaxes.text(
                event.xdata,
                event.ydata,
                text,
                ha='center',
                va='center',
                picker=5  # Make it selectable for a future 'select' tool
            )

            # The main application should handle adding the artist to its list
            if hasattr(main_window, '_add_annotation'):
                main_window._add_annotation(artist)
            else:
                logger.warning("MainWindow is missing the '_add_annotation' method.")
                self.figure.canvas.draw_idle()

            # Deactivate the tool after one use for convenience
            self.toolmanager.trigger_tool(self.name, 'tool_deactivated')

'''