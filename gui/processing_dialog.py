from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QComboBox, QFormLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QWidget, QGroupBox, QCheckBox, QFrame, QLayout
import json
import os
from DataManagement.module_loader import discover_modules
from localvars import PROCESSING_MODULES_DIR
from logger import get_logger
from gui.parameter_form_widget import ParameterFormWidget
import re
from gui.shared.smart_dialog import SmartDialog as QDialog

logger = get_logger(__name__)


class ProcessingDialog(QDialog):
    BASE_PARAMETERS = [
        # (name, label, type, required, placeholder)
        ('prefix', 'Prefix', str, False, 'Optional prefix for output files'),
        ('cooldown', 'Cooldown', 'label', False, ''),  # Will be set to cooldown name
    ]
    def __init__(self, file_path, module_type='pre', data_columns=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Processing Module")
        self.file_path = file_path
        self.module_type = module_type
        self.data_columns = data_columns or []
        self.selected_module = None
        self.params = {}
        self.parameter_form_widget = None
        # Extract cooldown from file_path
        self.cooldown = self._extract_cooldown(file_path)
        self.prefix_options = self._extract_prefix_options(file_path)
        self._init_ui()

    def _extract_cooldown(self, file_path):
        # Find the first folder after any of 'raw', 'preprocessed', or 'postprocessed' in the file path
        parts = os.path.normpath(file_path).split(os.sep)
        for key in ('raw', 'preprocessed', 'postprocessed'):
            try:
                idx = parts.index(key)
                if idx+1 < len(parts):
                    return parts[idx+1]
            except ValueError:
                logger.warning(f"No {key} folder found in {file_path}")
                continue
        return ''

    def _extract_prefix_options(self, file_path):
        # If filename starts with 6 digits, treat as date prefix
        fname = os.path.basename(file_path)
        m = re.match(r'(\d{6})', fname)
        return [m.group(1)] if m else []

    def _init_ui(self):
        layout = QVBoxLayout()
        # Module selection
        module_label = QLabel("Module:")
        self.module_combo = QComboBox()
        self.module_combo.setObjectName("module_combo") # For testing
        self.modules = self._discover_modules()
        self.module_combo.addItems([name for name, _, _ in self.modules])
        self.module_combo.currentIndexChanged.connect(self._on_module_changed)
        layout.addWidget(module_label)
        layout.addWidget(self.module_combo)

        # --- Base parameters at the top ---
        self.base_form = QFormLayout()
        self.base_param_widgets = {}
        for p in self.BASE_PARAMETERS:
            if p[0] == 'prefix' and self.prefix_options:
                name, label, typ, required, placeholder = ('prefix', 'Prefix', tuple(self.prefix_options), False, p[4])
            elif p[0] == 'cooldown' and self.cooldown:
                name, label, typ, required, placeholder = ('cooldown', 'Cooldown', 'label', False, self.cooldown)
            else:
                name, label, typ, required, placeholder = p if len(p) == 5 else (*p, None)
            w = self._make_widget_for_type(typ, placeholder)
            if placeholder and hasattr(w, 'setPlaceholderText') and typ not in ('label', 'checkbox'):
                w.setPlaceholderText(str(placeholder))
            if typ == 'checkbox' and placeholder:
                w.setChecked(bool(placeholder))
            self.base_form.addRow(label + (" *" if required else ""), w)
            self.base_param_widgets[name] = w
        base_group = QGroupBox("Global Parameters")
        base_group.setLayout(self.base_form)
        layout.addWidget(base_group)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # --- Module-specific parameters ---
        self.form_container = QWidget()
        self.form_container_layout = QVBoxLayout(self.form_container)
        self.form_container_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.form_container)
        # Import/Export buttons
        btns = QHBoxLayout()
        import_btn = QPushButton("Import Params")
        export_btn = QPushButton("Export Params")
        import_btn.clicked.connect(self.import_params)
        export_btn.clicked.connect(self.export_params)
        btns.addWidget(import_btn)
        btns.addWidget(export_btn)
        layout.addLayout(btns)
        # OK/Cancel
        ok_cancel = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        ok_cancel.addWidget(ok_btn)
        ok_cancel.addWidget(cancel_btn)
        layout.addLayout(ok_cancel)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)
        self._on_module_changed(0)

    def _discover_modules(self):
        # Use unified processing_modules folder and MODE constant
        mode = 'pre' if self.module_type == 'pre' else 'post'
        return discover_modules(PROCESSING_MODULES_DIR, mode)

    def _on_module_changed(self, idx):
        # Clear old widgets
        if self.parameter_form_widget:
            self.parameter_form_widget.deleteLater()
            self.parameter_form_widget = None

        if idx < 0 or idx >= len(self.modules):
            return

        _, cls, parameters = self.modules[idx]
        self.selected_module = cls
        # Create the new form widget
        self.parameter_form_widget = ParameterFormWidget(parameters, self.data_columns, self)
        self.form_container_layout.addWidget(self.parameter_form_widget)

    def _make_widget_for_type(self, typ, placeholder=None, required=True):
        if isinstance(typ, (tuple, list)):
            w = QComboBox()
            if not required:
                w.addItem("")
            w.addItems([str(v) for v in typ])
        elif typ == 'dropdown_column' or typ == 'dropdown':
            w = QComboBox()
            if not required:
                w.addItem("")
            w.addItems(self.data_columns)
        elif typ == 'checkbox' or typ == bool:
            w = QCheckBox()
        elif typ == 'label':
            w = QLabel(str(placeholder) if placeholder else '')
        else:
            w = QLineEdit()

        # Lets add the metadata as properties on the widget itself so we don't have to deal with the headache of searching for them
        w.setProperty('typ', typ)
        w.setProperty('placeholder', placeholder)
        w.setProperty('required', required)

        if placeholder and hasattr(w, 'setPlaceholderText') and typ not in ('label', 'checkbox'):
            w.setPlaceholderText(str(placeholder))
        if typ in [bool, 'checkbox'] and placeholder:
            w.setChecked(bool(placeholder))
        return w

    def _get_widget_value(self, w, typ, placeholder=None):
        # Handle checkboxes
        if isinstance(w, QCheckBox):
            return w.isChecked()
        # Handle labels
        if isinstance(w, QLabel):
            return w.text() if w.text() else (placeholder if placeholder else '')
        # Handle combo boxes and line edits
        if hasattr(w, 'currentText'): # QComboBox
            return w.currentText()
        if hasattr(w, 'text'): # QLineEdit, etc.
            val = w.text()
            if isinstance(typ, type) and typ is not str: # Try to cast to original type
                try:
                    return typ(val)
                except (ValueError, TypeError):
                    return val
            return val
        return placeholder if placeholder else ''

    def get_params(self, includeBaseParams=True):
        params = {}
        # Collect base params
        if includeBaseParams:
            for name, w in self.base_param_widgets.items():
                for p in self.BASE_PARAMETERS:
                    if p[0] == name:
                        typ = p[2]
                        placeholder = p[4] if len(p) == 5 else None
                        break
                params[name] = self._get_widget_value(w, typ, placeholder)
        # Collect module-specific params
        if self.parameter_form_widget:
            params.update(self.parameter_form_widget.get_params())
        return params

    def _validate_required_fields(self, params):
        # Validate base params
        for p in self.BASE_PARAMETERS:
            name, label, typ, required = p[:4]
            if required:
                val = params.get(name, None)
                if val is None or val == "" or (isinstance(val, bool) and not val):
                    raise ValueError(f"Required parameter '{label}' is missing.")
        # Validate module params
        if self.parameter_form_widget:
            # Call internal validation
            self.parameter_form_widget.validate()
            """
            param_defs = self.parameter_form_widget.param_defs
            for p_def in param_defs:
                d = self.parameter_form_widget._param_def_to_dict(p_def) if not isinstance(p_def, dict) else p_def
                if d.get('required'):
                    name = d['name'].split('_%d')[0] if d.get('name') else None
                    label = d.get('label')
                    val = params.get(name)
                    if val is None or val == "" or val == []:
                        raise ValueError(f"Required parameter '{label}' is missing.")
            """

    def import_params(self, file_path = None):
        if not file_path: # If not supplied, we simply ask
            file_path, _ = QFileDialog.getOpenFileName(self, "Import Parameters", "", "JSON Files (*.json)")
            if not file_path:
                return
        try:
            with open(file_path, 'r') as f:
                params = json.load(f)
            # Check for module key
            module_name = params.get('module', None)
            if module_name is None:
                QMessageBox.warning(self, "Import Error", "No module specified in parameter file.")
                logger.warning("No module specified in parameter file.")
                return
            # Find module index
            module_names = [name for name, _, _ in self.modules]
            if module_name not in module_names:
                QMessageBox.warning(self, "Import Error", f"Module '{module_name}' not found.")
                logger.warning(f"Module '{module_name}' not found.")
                return
            idx = module_names.index(module_name)
            self.module_combo.setCurrentIndex(idx)
            # This will update the form to the correct module
            params_to_set = {k: v for k, v in params.items() if k != 'module'}

            if self.parameter_form_widget:
                # The `set_params` in the widget is basic, but will work for simple key-value pairs.
                # A full implementation for multi-widgets would be more complex.
                self.parameter_form_widget.set_params(params_to_set)
            else:
                logger.error("Parameter form widget not available for setting parameters.")

        except Exception as e:
            QMessageBox.warning(self, "Import Error", str(e))
            logger.warning(f"Import Error: {e}")

    def export_params(self, file_path = None):
        try:
            params = self.get_params(includeBaseParams=False) # excluse base parameters
            # Add module name for context
            module_name = self.modules[self.module_combo.currentIndex()][0]
            params = {'module': module_name, **params}
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
            logger.warning(f"Export Error: {e}")
            return
        if not file_path: # If not supplied, we simply ask
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Parameters", "params.json", "JSON Files (*.json)")
            if not file_path:
                return
        try:
            with open(file_path, 'w') as f:
                json.dump(params, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
            logger.warning(f"Export Error: {e}")

    def accept(self):
        try:
            self.params = self.get_params()
            self.params['cooldown'] = self.cooldown # cooldown is not user-editable, but always included
            self._validate_required_fields(self.params)
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "Parameter Error", str(e))

    def get_selected_module(self):
        return self.get_selected_module_name(), self.selected_module, self.params 

    def get_selected_module_name(self):
        name, cls, _ = self.modules[self.module_combo.currentIndex()]
        if cls == self.selected_module:
            return name
        else:
            logger.warning(f"Selected module {self.selected_module} does not match module {name}")
            return None