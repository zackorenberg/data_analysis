from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QCheckBox,
    QPushButton, QLabel, QFileDialog, QGroupBox, QMessageBox, QWidget, QComboBox
)
from PyQt5.QtCore import pyqtSignal, Qt
import os
import json
from localvars import (
    SETTINGS_FILE, DEFAULT_SETTINGS, SETTINGS_METADATA, _get_nested_value, _set_nested_value,
    update_and_save_settings, get_current_settings, CACHING_MODULES_REGISTRY
)
from logger import get_logger
import importlib

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal(bool)  # Emits True if restart is required

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumWidth(500)
        self.current_settings = get_current_settings()  # Get a fresh copy of current settings
        self.ui_widgets = {}  # Stores references to the actual input widgets (QLineEdit, QCheckBox, etc.)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Group settings by their top-level key (e.g., "data_dirs", "behavior_flags")
        grouped_settings = {}
        for path, metadata in SETTINGS_METADATA.items():
            top_level_key = path.split('.')[0]
            if top_level_key not in grouped_settings:
                grouped_settings[top_level_key] = {}
            grouped_settings[top_level_key][path] = metadata

        for group_name, settings_in_group in grouped_settings.items():
            group_box = QGroupBox(group_name.replace('_', ' ').title())  # Title case for group box
            form_layout = QFormLayout()

            # Sort settings within the group for consistent UI order
            sorted_paths = sorted(settings_in_group.keys())

            for path in sorted_paths:
                metadata = settings_in_group[path]
                label = metadata["label"]
                widget_type = metadata["type"]

                # Get current value from the loaded settings
                keys = path.split('.')
                current_value = _get_nested_value(self.current_settings, keys)

                widget = None
                # Add QDoubleValidator and QIntValidator if needed
                # self.int_validator = QIntValidator()
                # self.float_validator = QDoubleValidator()

                if widget_type == "directory_path":
                    widget, line_edit = self._create_path_selector(current_value, f"Select {label}")
                    self.ui_widgets[path] = line_edit  # Store the QLineEdit for easy access
                elif widget_type == "checkbox":
                    widget = QCheckBox()
                    widget.setChecked(bool(current_value))
                    self.ui_widgets[path] = widget
                elif widget_type == "string":
                    widget = QLineEdit(str(current_value))
                    self.ui_widgets[path] = widget
                elif widget_type == "integer":
                    widget = QLineEdit(str(current_value))
                    # widget.setValidator(self.int_validator)
                    self.ui_widgets[path] = widget
                elif widget_type == "float":
                    widget = QLineEdit(str(current_value))
                    # widget.setValidator(self.float_validator)
                    self.ui_widgets[path] = widget
                # Add more widget types as needed (e.g., 'dropdown', 'color_picker')

                if widget:
                    form_layout.addRow(label + ":", widget)

            group_box.setLayout(form_layout)
            main_layout.addWidget(group_box)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save_settings_and_close)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

    def _create_path_selector(self, initial_path, dialog_title):
        """Helper to create a QLineEdit with a browse button for directory selection."""
        hbox = QHBoxLayout()
        line_edit = QLineEdit(initial_path)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(lambda: self._browse_directory(line_edit, dialog_title))
        hbox.addWidget(line_edit)
        hbox.addWidget(browse_button)
        widget = QWidget()  # Container widget for the layout
        widget.setLayout(hbox)
        return widget, line_edit  # Return both the container and the line_edit

    def _browse_directory(self, line_edit, dialog_title):
        """Opens a directory dialog and updates the QLineEdit."""
        directory = QFileDialog.getExistingDirectory(self, dialog_title, line_edit.text())
        if directory:
            line_edit.setText(directory)

    def _get_settings_from_ui(self):
        """Collects current settings from UI elements dynamically."""
        new_settings = get_current_settings()  # Start with a copy of current settings

        for path, widget in self.ui_widgets.items():
            keys = path.split('.')
            value = None
            if isinstance(widget, QLineEdit):
                value = widget.text()
                # Attempt to convert to correct type if metadata specifies
                metadata = SETTINGS_METADATA[path]
                if metadata["type"] == "integer":
                    try:
                        value = int(value)
                    except ValueError:
                        value = 0  # Default or handle error
                elif metadata["type"] == "float":
                    try:
                        value = float(value)
                    except ValueError:
                        value = 0.0  # Default or handle error
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QComboBox):  # If you add dropdowns
                value = widget.currentText()

            if value is not None:
                _set_nested_value(new_settings, keys, value)

        return new_settings

    def _save_settings_and_close(self):
        """Saves settings to file and emits signal, checking if restart is required."""
        new_settings = self._get_settings_from_ui()

        restart_required = False
        for path, metadata in SETTINGS_METADATA.items():
            if metadata.get("restart_required", False):
                keys = path.split('.')
                old_value = _get_nested_value(self.current_settings, keys)
                new_value = _get_nested_value(new_settings, keys)
                if old_value != new_value:
                    restart_required = True
                    break  # Only one restart-requiring change is enough

        # Save the settings to file using the localvars function
        try:
            update_and_save_settings(new_settings)  # This updates _current_settings and saves to file
            logger.info(f"Settings saved to {SETTINGS_FILE}.")
            self.settings_saved.emit(restart_required)
            self.accept()  # Close the dialog
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")
            logger.error(f"Failed to save settings: {e}")
