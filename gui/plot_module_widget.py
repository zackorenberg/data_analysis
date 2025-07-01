import os
import sys
import importlib.util
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel,
    QScrollArea, QMessageBox, QDockWidget, QDialog, QFormLayout, QDialogButtonBox,
    QLineEdit, QComboBox, QColorDialog, QFileDialog, QTextEdit
)
from PyQt5.QtCore import pyqtSignal, QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from logger import get_logger

def validate_bool(b): # Copied verbatim from matplotlib.rcsetup to avoid import
    """Convert b to ``bool`` or raise."""
    if isinstance(b, str):
        b = b.lower()
    if b in ('t', 'y', 'yes', 'on', 'true', '1', 1, True):
        return True
    elif b in ('f', 'n', 'no', 'off', 'false', '0', 0, False):
        return False
    else:
        raise ValueError(f'Cannot convert {b!r} to bool')

logger = get_logger(__name__)


class PlotModule:
    """Base class for plot modules"""
    name = "Base Plot Module"
    description = "Base Plot Module - You should never see this text"

    reset_plot = False # This flag should be set to true should any modifications require a reset (init and disable)

    def __init__(self, params = None):
        self.params = params or {}

    def initialize(self):
        """
        Possible functions to be called before mpl canvas is created, this is typically to affect global settings (i.e. styles)
        If the initialization function requires a full plot reset, it must return True
        """
        pass

    def plot(self, ax):
        """Main plotting function - override in subclasses"""
        pass

    def disable(self, ax):
        """
        For the event that a plot is disabled.
        If the disable function requires a full plot reset, it must return True
        """
        pass

def discover_plot_modules(modules_dir="plot_modules"):
    """
    Discover plot modules from the specified directory.
    Returns a list of (module_name, module_class, description) tuples.
    """
    plot_modules = []
    if not os.path.exists(modules_dir):
        print(f"Plot modules directory not found: {modules_dir}")
        return plot_modules

    # Look for Python files in the modules directory
    for filename in os.listdir(modules_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            module_path = os.path.join(modules_dir, filename)

            try:
                # Load the module
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for a class that inherits from PlotModule
                for attr_name in dir(module):
                    if attr_name.startswith('__'): continue
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and issubclass(attr, PlotModule) and attr != PlotModule):
                        # Check if it has the required attributes
                        #if hasattr(attr, 'name') and hasattr(attr, 'description'): dont need to check, just instead throw an erro
                        # PARAMETERS can be overridden within the class. Default to module parameters if not present.
                        parameters = getattr(attr, 'PARAMETERS', getattr(module, 'PARAMETERS', []))

                        plot_modules.append((f"{module_name}.{attr_name}", attr, attr.description, parameters))
                        # break we can have multiple from one file?

            except Exception as e:
                print(f"Error loading plot module {filename}: {e}")

    return plot_modules


class PlotModuleWidget(QWidget):
    """
    A dockable widget for selecting and managing plot modules.
    It discovers modules, displays them as a checklist with configuration options,
    and emits a signal with configured module instances when selections are applied.
    """
    modulesChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.discovered_modules = []
        # Dictionary to store user-defined configurations for each module
        self.module_configs = {}

        self._init_ui()
        self._load_modules()

    def _init_ui(self):
        layout = QVBoxLayout()
        desc_label = QLabel("Select modules to apply to the plot.")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.modules_container = QWidget()
        self.modules_layout = QVBoxLayout(self.modules_container)
        self.modules_layout.setSpacing(4)
        self.modules_layout.setContentsMargins(5, 5, 5, 5)
        scroll_area.setWidget(self.modules_container)
        layout.addWidget(scroll_area)

        btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.deselect_all_btn = QPushButton("Deselect All")
        self.apply_btn = QPushButton("Apply")
        self.refresh_btn = QPushButton("Reload")
        self.import_btn = QPushButton("Import")
        self.export_btn = QPushButton("Export")

        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.deselect_all_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.apply_btn)
        layout.addLayout(btn_layout)

        self.select_all_btn.clicked.connect(self.select_all_modules)
        self.deselect_all_btn.clicked.connect(self.deselect_all_modules)
        self.apply_btn.clicked.connect(self.apply_modules)
        self.refresh_btn.clicked.connect(self.reload_modules)
        self.import_btn.clicked.connect(self.import_module_config)
        self.export_btn.clicked.connect(self.export_module_config)

        self.setLayout(layout)


    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _load_modules(self):
        self._clear_layout(self.modules_layout)
        self.discovered_modules = discover_plot_modules()

        if not self.discovered_modules:
            no_modules_label = QLabel("No plot modules found in 'plot_modules' directory.")
            self.modules_layout.addWidget(no_modules_label)
        else:
            for module_name, module_class, description, parameters in self.discovered_modules:
                # Each module is now a widget with its own horizontal layout
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)

                checkbox = QCheckBox(module_class.name)
                checkbox.setToolTip(description)
                checkbox.setProperty("module_name", module_name)
                row_layout.addWidget(checkbox)
                row_layout.addStretch()

                # If the module has parameters, add a "Configure" button
                if parameters:
                    config_btn = QPushButton("Configure...")
                    config_btn.setProperty("module_name", module_name)
                    config_btn.clicked.connect(self._open_config_dialog)
                    row_layout.addWidget(config_btn)

                self.modules_layout.addWidget(row_widget)

        self.modules_layout.addStretch(1)


    def _checked_modules(self):
        """Loads which modules are currently checked, for use on reloading modules"""
        checked_modules = [] # Can be set but with overhead
        for i in range(self.modules_layout.count()):
            row_widget = self.modules_layout.itemAt(i).widget()
            if not isinstance(row_widget, QWidget): continue

            checkbox = row_widget.findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                if checkbox.property("module_name"):
                    checked_modules.append(checkbox.property("module_name"))

        return checked_modules

    def _check_modules(self, modules):
        """Checks a list of specified modules"""
        for i in range(self.modules_layout.count()):
            row_widget = self.modules_layout.itemAt(i).widget()
            if not isinstance(row_widget, QWidget): continue

            checkbox = row_widget.findChild(QCheckBox)
            if checkbox and checkbox.property("module_name") in modules:
                checkbox.setChecked(True)


    def _open_config_dialog(self):
        """Opens the configuration dialog for a specific module."""
        sender_btn = self.sender()
        module_name = sender_btn.property("module_name")

        # Find the module's definition
        module_def = next((m for m in self.discovered_modules if m[0] == module_name), None)

        if not module_def:
            return

        _, module_class, _, parameters = module_def

        # Get the currently stored configuration for this module
        current_config = self.module_configs.get(module_name, {})

        dialog = ModuleConfigDialog(module_class.name, parameters, current_config, self)
        if dialog.exec_() == QDialog.Accepted:
            # If user clicks OK, save the new configuration
            self.module_configs[module_name] = dialog.get_params()
            self._check_modules([module_name]) # Add check


    def select_all_modules(self):
        for i in range(self.modules_layout.count()):
            widget = self.modules_layout.itemAt(i).widget()
            if widget and isinstance(widget, QWidget):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def deselect_all_modules(self):
        for i in range(self.modules_layout.count()):
            widget = self.modules_layout.itemAt(i).widget()
            if widget and isinstance(widget, QWidget):
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)

    def _reload_modules(self):
        """
        Just reloads the actual modules and updates the layout, does not apply them
        """
        checked_modules = self._checked_modules()
        self._clear_layout(self.modules_layout)
        self._load_modules()
        self._check_modules(checked_modules)

    def reload_modules(self):
        """Reloads and applies all modules on demand (say a user changed one, for example)"""
        self._reload_modules()
        self.apply_modules()

    def apply_modules(self):
        """Instantiates selected modules with their configs and emits the signal."""
        enabled_instances = self.export_modules()
        QMessageBox.information(self, "Modules Applied", f"Applied {len(enabled_instances)} plot module(s).")
        self.modulesChanged.emit(enabled_instances) # Do i keep this here?

    def export_modules(self):
        """
        Exports current list of enabled instances by request
        """
        enabled_instances = []

        # Find which modules are checked in the UI
        for i in range(self.modules_layout.count()):
            row_widget = self.modules_layout.itemAt(i).widget()
            if not isinstance(row_widget, QWidget): continue

            checkbox = row_widget.findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                module_name = checkbox.property("module_name")
                module_def = next((m for m in self.discovered_modules if m[0] == module_name), None)

                if module_def:
                    _, module_class, _, _ = module_def
                    # Get config for this module, or an empty dict if none
                    config = self.module_configs.get(module_name, {})
                    try:
                        # Pass the config to the module's constructor
                        instance = module_class(params=config)
                        enabled_instances.append(instance)
                    except Exception as e:
                        logger.error(f"Error creating instance of {module_class.name}: {e}")

        return enabled_instances


    def export_module_config(self, file_path = None):
        """Saves the current module selections and configurations to a JSON file."""
        logger.debug("Exporting module configuration.")

        config_data = {
            'active_modules': self._checked_modules(),
            'configurations': self.module_configs
        }
        if not file_path: # If not supplied, we simply ask
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Module Configuration", "plot_modules.json", "JSON Files (*.json)")
            if not file_path: # If still not given, we return
                return

        try:
            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            QMessageBox.information(self, "Export Successful", f"Module configuration saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to save configuration: {e}")
            logger.error(f"Failed to export module config: {e}")


    def import_module_config(self, file_path = None):
        """Loads module selections and configurations from a JSON file."""
        logger.debug("Importing module configuration.")

        if not file_path: # If not supplied, we simply ask
            file_path, _ = QFileDialog.getOpenFileName(self, "Import Module Configuration", "plot_modules.json", "JSON Files (*.json)")
            if not file_path:
                return

        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Failed to read or parse file: {e}")
            logger.error(f"Failed to import module config: {e}")
            return

        # Validate the imported data
        if 'active_modules' not in config_data or 'configurations' not in config_data:
            QMessageBox.warning(self, "Import Error", "Invalid configuration file format.")
            return

        # Update the internal state
        self.module_configs = config_data.get('configurations', {})
        active_modules_to_check = config_data.get('active_modules', [])

        # Update the UI
        self.deselect_all_modules()
        self._check_modules(active_modules_to_check)

        # Apply the changes
        self.apply_modules()
        logger.info("Module configuration loaded and applied.")


class ColorButton(QPushButton):
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(40, 24))
        self._color = color
        self.setToolTip("Choose Color")
        self.update_style()
        self.clicked.connect(self.choose_color)

    def set_color(self, color):
        self._color = color
        self.update()
        self.update_style()

    def get_color(self):
        return self._color

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        rect = self.rect().adjusted(4, 4, -4, -4)
        if self._color:
            painter.setBrush(self._color)
            painter.setPen(QPen(QColor('black'), 1))
            painter.drawRect(rect)
        else:
            painter.setBrush(QColor('white'))
            painter.setPen(QPen(QColor('black'), 1))
            painter.drawRect(rect)
            # Draw red diagonal line
            pen = QPen(QColor('red'), 2)
            painter.setPen(pen)
            painter.drawLine(rect.topLeft(), rect.bottomRight())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.RightButton:
            self.remove_color()

    def update_style(self):
        if self._color:
            self.setStyleSheet(f"background-color: {self._color.name()}; border: 1px solid #888;")
        else:
            self.setStyleSheet("background-color: white; border: 1px solid #888;")

    def choose_color(self):
        color = QColorDialog.getColor(self._color or QColor(0, 0, 0), None, "Choose Color")
        if color.isValid():
            self.set_color(color)

    def remove_color(self):
        self.set_color(None)


class ModuleConfigDialog(QDialog):
    """
    A generic dialog to configure module parameters.
    It dynamically builds a form based on a PARAMETERS definition list.
    """

    def __init__(self, module_name, parameters, current_values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configure: {module_name}")
        self.setMinimumWidth(350)

        self.parameters = parameters
        self.current_values = current_values or {}
        self.param_widgets = {}

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Build the form from the parameter definitions
        for name, label, typ, _, default in parameters:
            widget = self._make_widget_for_type(typ, default)

            # Set the widget's current value from saved config or default
            current_val = self.current_values.get(name, default)
            self._set_widget_value(widget, current_val)

            form_layout.addRow(f"{label}:", widget)
            self.param_widgets[name] = widget

        layout.addLayout(form_layout)
        # New buttons, adding a reset to default option:
        button_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch(1)
        # OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        layout.addLayout(button_layout)
        #layout.addWidget(button_box)

    def reset_to_defaults(self):
        """
        Resets all parameter widgets in the dialog to their default values
        as defined in the module's PARAMETERS list.
        """
        for name, label, typ, required, default_value in self.parameters:
            if name in self.param_widgets:
                widget = self.param_widgets[name]
                # Special handling for color type, as its default_value might be a string like 'gray'
                # and needs to be processed by _process_mpl_color_default before setting on ColorButton.
                if typ == 'color':
                    processed_default = self._process_mpl_color_default(default_value)
                    if processed_default:
                        widget.set_color(QColor(processed_default))
                    else:
                        widget.set_color(None)  # Clear the color if default is None/empty
                else:
                    self._set_widget_value(widget, default_value)
        #QMessageBox.information(self, "Reset", "Parameters reset to default values.")

    def _process_mpl_color_default(self, value):
        """Small helper to process mpl rcparam color values"""
        if not value:
            return None
        if type(value) == str:
            if value in ['None', 'auto', 'inherit']:
                return None
            # Test if float
            try:
                value = float(value)
                value *= (255 if value <= 1 else 1)
                value = int(value)
                return QColor(value, value, value, 1).name()
            except ValueError:
                pass
        if type(value) == float:
            value *= (255 if value <= 1 else 1)
            value = int(value)
            return QColor(value, value, value, 1).name()
        if type(value) == int:
            return QColor(value, value, value, 1).name()
        return value

    def _make_widget_for_type(self, typ, default_value):
        """Creates the appropriate QWidget for a given parameter type."""
        if isinstance(typ, (list, tuple)):
            widget = QComboBox()
            widget.addItems([str(v) for v in typ])
        elif typ == bool or typ == 'checkbox':
            widget = QCheckBox()
        elif typ == 'color':
            widget = ColorButton()
            if default_value:
                default_value = self._process_mpl_color_default(default_value)
                if default_value: # this case we'd want it to be clear and handled by mpl
                    widget.set_color(QColor(default_value))
        elif typ == 'textarea':  # <-- ADD THIS BLOCK
            widget = QTextEdit()
            widget.setAcceptRichText(False)  # Ensure plain text for code
            widget.setMinimumHeight(150)  # Give it a reasonable default size
            if default_value is not None:
                # QTextEdit doesn't have a placeholder, so we set initial text
                widget.setPlainText(str(default_value))
        else:  # Handles str, int, float, etc.
            widget = QLineEdit()
            if default_value is not None:
                widget.setPlaceholderText(str(default_value))
        return widget

    def _set_widget_value(self, widget, value):
        """Sets the value of a widget, handling different widget types."""
        if value is None:
            return

        if isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index > -1:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(validate_bool(value))
        elif isinstance(widget, QTextEdit):
            widget.setPlainText(str(value))
        elif isinstance(widget, ColorButton):
            try:
                value = self._process_mpl_color_default(value)
                if value:
                    widget.set_color(QColor(value))
            except Exception as e:
                logger.info(f"Could not set color widget to {value}: {e}")
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))

    def get_params(self):
        """Reads the configured values from the widgets and returns them as a dict."""
        params = {}
        for name, widget in self.param_widgets.items():
            # Find the original parameter definition to get the type
            param_def = next((p for p in self.parameters if p[0] == name), None)
            typ = param_def[2] if param_def else str
            value = None

            if isinstance(widget, QComboBox):
                value = widget.currentText()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
                params[name] = value
                continue
            elif isinstance(widget, ColorButton):
                color = widget.get_color()
                value = color.name() if color else None
            elif isinstance(widget, QLineEdit):
                value = widget.text()
                # Try to cast to the correct type (e.g., float, int)
                if isinstance(typ, type) and value:
                    try:
                        value = typ(value)
                    except (ValueError, TypeError):
                        # On failure, use the default value from the definition
                        value = param_def[4] if param_def else None
                elif not value:
                    value = param_def[4] if param_def else None
            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText()
            if (param_def and param_def[3]) and not value:
                QMessageBox.warning(self, f"Missing Parameter: {name}", f"You must specify a value for this parameter: '{param_def[1]}'.")
                return {} # We wont specify any parameters


            if value: # We don't want to give None values!
                params[name] = value

        return params