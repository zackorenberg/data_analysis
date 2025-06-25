from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFormLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QWidget, QGroupBox, QCheckBox, QFrame, QLayout
from PyQt5.QtCore import Qt
import json
import os
from DataManagement.module_loader import discover_modules
from processing_base import BasePreprocessingModule, BasePostprocessingModule
import re
from localvars import PROCESSING_MODULES_DIR
from logger import get_logger

logger = get_logger(__name__)


# FieldRole and LabelRole constants for QFormLayout
FieldRole = 1  # QFormLayout.FieldRole
LabelRole = 0  # QFormLayout.LabelRole

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
        self.param_widgets = {}
        self.params = {}
        self.multi_param_widgets = {}  # base_name: [widgets]
        self.multi_param_groups = {}   # base_name: groupbox
        self.widget_to_varname = {}   # widget: varname for multi-groups
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
        self.form = QFormLayout()
        self.form_widget = QVBoxLayout()
        self.form_widget.addLayout(self.form)
        layout.addLayout(self.form_widget)
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
        for i in reversed(range(self.form.count())):
            item = self.form.itemAt(i)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()
        self.param_widgets.clear()
        self.multi_param_widgets = {}
        self.multi_param_groups = {}
        self.widget_to_varname = {}
        if idx < 0 or idx >= len(self.modules):
            return
        _, cls, parameters = self.modules[idx]
        self.selected_module = cls
        self._build_param_form(parameters, self.form, self.param_widgets, self.multi_param_widgets, self.multi_param_groups, self.widget_to_varname)


    def _create_multi_groupbox_layout(self, add_funct, add_params, label=None):
        super_group = QGroupBox()
        if label:
            super_group.setTitle(label)
        super_layout = QVBoxLayout()
        super_group.setLayout(super_layout)
        add_fresh_btn = QPushButton("+")
        super_layout.addWidget(add_fresh_btn)
        def add_fresh_group(*args):
            return lambda: add_funct(*args, parent_layout=super_layout)
        add_fresh_btn.clicked.connect(add_fresh_group(*add_params))
        return super_group, super_layout

    def _build_param_form(self, param_defs, parent_layout, param_widgets, multi_param_widgets, multi_param_groups, widget_to_varname, parent_base=None):
        for param in param_defs:
            d = self._param_def_to_dict(param) if not isinstance(param, dict) else param
            name, label, typ, required, placeholder = d['name'], d['label'], d['typ'], d['required'], d['placeholder']
            required = bool(required) if required is not None else False
            label = label if label is not None else base_name
            rlabel = f"{label} *" if required else label
            name = name if name is not None else ''
            typ = typ if typ is not None else ''
            placeholder = placeholder if placeholder is not None else ''
            m = re.match(r'(.+)_%d$', name) if name else None
            # Multi-group (dict type)
            if m and isinstance(typ, dict) and typ.get('type') == 'multi':
                base_name = m.group(1)
                if base_name not in multi_param_groups:
                    multi_param_groups[base_name] = []
                    super_group, super_layout = self._create_multi_groupbox_layout(self._add_multi_group, (base_name, label, typ['fields'], required), label=rlabel)
                    
                    self._add_multi_group(base_name, label, typ['fields'], required, super_layout)
                    parent_layout.addRow(super_group)
                continue
            # Multi-value (single type, not dict)
            elif m:
                logger.debug(f"Multi-value param: {name}")
                base_name = m.group(1)
                if base_name not in multi_param_widgets:
                    multi_param_widgets[base_name] = []
                    super_group, super_layout = self._create_multi_groupbox_layout(self._add_multi_param_row, (base_name, label, typ, required), label=rlabel)
                    self._add_multi_param_row(base_name, label, typ, required, super_layout, is_first=True)
                    parent_layout.addRow(super_group)
                continue
            # Standalone multi-group
            if isinstance(typ, dict) and typ.get('type') == 'multi':
                base_name = name
                if base_name not in multi_param_groups:
                    multi_param_groups[base_name] = []
                    self._add_multi_group(base_name, label, typ['fields'], required, parent_layout)
                continue
            w = self._make_widget_for_type(typ, placeholder, required)
            label_text = label + (" *" if required else "")
            parent_layout.addRow(label_text, w)
            if not parent_base:
                param_widgets[name] = w
            if parent_base:
                widget_to_varname[w] = name

    def _add_multi_param_row(self, base_name, label, typ, required, parent_layout, insert_after=None, placeholder=None, is_first=False):
        def add_row(after_idx=None):
            w = self._make_widget_for_type(typ, placeholder, required)
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            # Only the first row gets the label and plus button
            """ we are using the other layout function instead of this, with the plus button on the bottom
            if (is_first or (after_idx is not None and after_idx == 0)) and len(self.multi_param_widgets[base_name]) == 0:
                label_layout = QHBoxLayout()
                label_widget = QLabel(label + (" *" if required else ""))
                plus_btn = QPushButton("+")
                label_layout.addWidget(label_widget)
                label_layout.addWidget(plus_btn)
                label_container = QWidget()
                label_container.setLayout(label_layout)
                if type(parent_layout) == QFormLayout:
                    parent_layout.insertRow(0, label_container)
                else:
                    parent_layout.insertWidget(0, label_container)

                plus_btn.clicked.connect(lambda: add_row(len(self.multi_param_widgets[base_name])))
            """
            row_layout.addWidget(w)
            
            

            minus_btn = QPushButton("–")
            #row_layout.addWidget(minus_btn)
            #""" this is buggy depending on the order you press the buttons
            plus_btn = QPushButton("+")
            row_layout.addWidget(plus_btn)
            row_layout.addWidget(minus_btn)
            #"""
            minus_btn.clicked.connect(lambda: self._remove_multi_param_row(base_name, container, parent_layout, required))

            container = QWidget()
            container.setLayout(row_layout)

            def find_next_row_lambda(base_name, container):
                def find_next_row():
                    for i, (w, cont) in enumerate(self.multi_param_widgets[base_name]):
                        if cont == container:
                            return i
                    return None
                return lambda: add_row(find_next_row())
            
            plus_btn.clicked.connect(find_next_row_lambda(base_name, container))
            # Determine index for insertion
            if after_idx is None:
                idx = len(self.multi_param_widgets[base_name])
            else:
                idx = after_idx + 1
            self.multi_param_widgets[base_name].insert(idx, (w, container))
            if type(parent_layout) == QFormLayout:
                parent_layout.insertRow(idx, container)
            else:
                parent_layout.insertWidget(idx, container)
        add_row(insert_after)

    def _remove_multi_param_row(self, base_name, container, parent_layout, required=False):
        widgets = self.multi_param_widgets[base_name]
        """ I believe this is handled later
        if required and len(widgets) <= 1:
            QMessageBox.warning(self, "Cannot Remove", "At least one value is required for this field.")
            return
        """
        for i, (w, cont) in enumerate(widgets):
            if cont == container:
                if type(parent_layout) == QFormLayout:
                    parent_layout.removeRow(cont)
                else:
                    parent_layout.removeWidget(cont)
                cont.deleteLater()
                widgets.pop(i)
                break

    def _add_multi_group(self, base_name, label, fields, required, parent_layout, insert_after=None):
        def add_group(after_idx=None):
            groupbox = QGroupBox()
            vbox = QFormLayout()
            groupbox.setLayout(vbox)
            minus_btn = QPushButton("–")
            plus_btn = QPushButton("+")
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(plus_btn)
            btn_layout.addWidget(minus_btn)
            vbox.addRow(btn_layout)
            # Recursively build subfields
            self._build_param_form(fields, vbox, self.param_widgets, self.multi_param_widgets, self.multi_param_groups, self.widget_to_varname, parent_base=base_name)
            # Determine index for insertion
            if after_idx is None:
                idx = len(self.multi_param_groups[base_name])
            else:
                idx = after_idx + 1
            self.multi_param_groups[base_name].insert(idx, (groupbox, vbox))
            label_text = f"{label} {idx+1}" + (" *" if required else "")
            groupbox.setTitle(label_text)
            if type(parent_layout) == QFormLayout:
                parent_layout.insertRow(idx, groupbox)
            else:
                parent_layout.insertWidget(idx, groupbox)

            def find_next_row_lambda(base_name, groupbox):
                def find_next_row():
                    for i, (gb, vbox) in enumerate(self.multi_param_groups[base_name]):
                        if gb == groupbox:
                            return i
                    return None
                return lambda: add_group(find_next_row())

            #plus_btn.clicked.connect(lambda: add_group(idx))
            plus_btn.clicked.connect(find_next_row_lambda(base_name, groupbox))
            minus_btn.clicked.connect(lambda: self._remove_multi_group(base_name, groupbox, parent_layout, label, required))
            self._update_multi_group_labels(base_name, parent_layout, label, required)
            # For all widgets in vbox, track their varnames
            """ I dont think this does anything
            for subparam in fields:
                subname, *_,= subparam
                key = f"{base_name}.{subname}"
                w = self.param_widgets.get(key)
                if w:
                    self.widget_to_varname[w] = subname
            """
        add_group(insert_after)

    def _remove_multi_group(self, base_name, groupbox, parent_layout, label=None, required=None):
        for i, (gb, vbox) in enumerate(self.multi_param_groups[base_name]):
            if gb == groupbox:
                if type(parent_layout) == QFormLayout:
                    parent_layout.removeRow(gb)
                else:
                    parent_layout.removeWidget(gb)
                self.multi_param_groups[base_name].pop(i)
                gb.deleteLater()
                break
        
        self._update_multi_group_labels(base_name, parent_layout, label=label, required=required)

    def _update_multi_group_labels(self, base_name, parent_layout, label=None, required=None):
        for idx, (gb, vbox) in enumerate(self.multi_param_groups[base_name]):
            label_text = f"{label} {idx+1}" + (" *" if required else "")
            gb.setTitle(label_text)

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
        elif typ == 'checkbox':
            w = QCheckBox()
        elif typ == 'label':
            w = QLabel(str(placeholder) if placeholder else '')
        else:
            w = QLineEdit()
        if placeholder and hasattr(w, 'setPlaceholderText') and typ not in ('label', 'checkbox'):
            w.setPlaceholderText(str(placeholder))
        if typ == 'checkbox' and placeholder:
            w.setChecked(bool(placeholder))
        return w

    def _get_widget_value(self, w, typ, placeholder=None):
        # Handle checkboxes
        if isinstance(w, QCheckBox):
            return w.isChecked()
        # Handle labels
        if isinstance(w, QLabel):
            return w.text() if w.text() else (placeholder if placeholder else '')
        # Handle combo boxes
        if isinstance(w, QComboBox):
            return w.currentText()
        # Handle line edits
        if isinstance(w, QLineEdit):
            val = w.text()
            # Try to convert to the correct type if typ is a type
            if isinstance(typ, type) and typ is not str:
                try:
                    return typ(val)
                except Exception as e:
                    logger.warning(f"Error converting value to type {typ}: {e}")
                    return val
            return val
        # Fallback
        if hasattr(w, 'text'):
            logger.warning(f"Widget hit fallback {w} has text: {w.text()}")
            return w.text()
        return placeholder if placeholder else ''
    
    
    def _set_widget_value(self, w, value):
        if isinstance(w, QComboBox):
            idx = w.findText(value)
            if idx >= 0:
                w.setCurrentIndex(idx)
        elif isinstance(w, QCheckBox):
            w.setChecked(value)
        elif isinstance(w, QLineEdit):
            w.setText(value)
        elif isinstance(w, QLabel):
            w.setText(value)
        else:
            logger.warning(f"Widget hit fallback {w} has text: {w.text()}")
            w.setText(value)

    def _collect_param_form(self, param_widgets, multi_param_widgets, multi_param_groups):
        params = {}
        # Single-value params
        for name, w in param_widgets.items():
            # Skip base params if present
            if hasattr(self, 'base_param_widgets') and name in self.base_param_widgets:
                logger.warning(f"Skipping parameter: {name}, already exists as base parameter")
                continue
            typ = None
            placeholder = None
            params[name] = self._get_widget_value(w, typ, placeholder)
        # Multi-value params
        for base_name, widgets in multi_param_widgets.items():
            values = []
            for w, _ in widgets:
                v = self._get_widget_value(w, None)
                if v != "":
                    values.append(v)
            params[base_name] = values
        # Multi-group params
        for base_name, groups in multi_param_groups.items():
            group_values = []
            for groupbox, vbox in groups:
                group_params = {}
                for i in range(vbox.rowCount()):
                    item = vbox.itemAt(i, FieldRole)
                    if item is not None and item.widget() is not None:
                        w = item.widget()
                        varname = self.widget_to_varname.get(w)
                        if not varname:
                            continue
                        v = self._get_widget_value(w, None)
                        if v != "":
                            group_params[varname] = v
                if len(group_params.keys()):
                    group_values.append(group_params)
            params[base_name] = group_values
        return params

    def get_params(self, includeBaseParams=True):
        params = {}
        # Collect base params
        if includeBaseParams:
            for name, w in self.base_param_widgets.items():
                typ = None
                for p in self.BASE_PARAMETERS:
                    if p[0] == name:
                        typ = p[2]
                        placeholder = p[4] if len(p) == 5 else None
                        break
                params[name] = self._get_widget_value(w, typ, placeholder)
        # Collect module-specific params
        params.update(self._collect_param_form(self.param_widgets, self.multi_param_widgets, self.multi_param_groups))
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
        _, _, param_defs = self.modules[self.module_combo.currentIndex()]
        param_defs_by_name = {p[0].split('_%d')[0]: p for p in param_defs if not isinstance(p, dict)}
        # Single-value
        for name, w in self.param_widgets.items():
            if hasattr(self, 'base_param_widgets') and name in self.base_param_widgets:
                continue
            if name in param_defs_by_name:
                _, label, typ, required = param_defs_by_name[name][:4]
                if required:
                    val = params.get(name, None)
                    if val is None or val == "" or (isinstance(val, bool) and not val):
                        raise ValueError(f"Required parameter '{label}' is missing.")
        # Multi-value
        for base_name, widgets in self.multi_param_widgets.items():
            if base_name in param_defs_by_name:
                _, label, typ, required = param_defs_by_name[base_name][:4]
                if required:
                    values = params.get(base_name, [])
                    if not values:
                        raise ValueError(f"At least one value required for '{label}'.")
        # Multi-group
        for base_name, groups in self.multi_param_groups.items():
            if base_name in param_defs_by_name:
                _, label, typ, required = param_defs_by_name[base_name][:4]
                if required:
                    group_values = params.get(base_name, [])
                    if not group_values:
                        raise ValueError(f"At least one group required for '{label}'.")

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
            # Remove 'module' key from params for the rest
            # TODO: Test if it actually changes and updates the form
            params = {k: v for k, v in params.items() if k != 'module'}
            # Single-value params
            for name, w in self.param_widgets.items():
                if name in params:
                    self._set_widget_value(w, params[name])
                    
            # Get parameter definitions for the current module
            _, _, param_defs = self.modules[self.module_combo.currentIndex()]
            # can do re.match(r'(.+)_%d$', p[0]).group(1) instead of split()[0]
            param_defs_by_name = {p[0].split('_%d')[0]: p for p in param_defs if not isinstance(p, dict)}
            # Multi-value params
            for base_name, widgets in self.multi_param_widgets.items():
                values = params.get(base_name, [])
                # Get label, typ, required from param_defs
                if base_name in param_defs_by_name:
                    _, label, typ, required = param_defs_by_name[base_name][:4]
                else:
                    logger.warning(f"Base name {base_name} not found in param_defs")
                    label, typ, required = base_name, None, False
                # Remove all but one row, then add as needed
                while len(widgets) > 1:
                    _, cont = widgets[-1]
                    self._remove_multi_param_row(base_name, cont, self.form)
                for i, v in enumerate(values):
                    if i >= len(self.multi_param_widgets[base_name]):
                        self._add_multi_param_row(base_name, label, typ, required, self.form)
                    w, _ = self.multi_param_widgets[base_name][i]
                    self._set_widget_value(w, v)
            # Multi-group params
            for base_name, groups in self.multi_param_groups.items():
                group_values = params.get(base_name, [])
                # Get label, fields, required from param_defs
                if base_name in param_defs_by_name:
                    _, label, typ, required = param_defs_by_name[base_name][:4]
                    fields = typ['fields'] if isinstance(typ, dict) and 'fields' in typ else []
                else:
                    logger.warning(f"Multi-group base name {base_name} not found in param_defs")
                    label, fields, required = base_name, [], False
                # Remove all but one group, then add as needed
                while len(groups) > 1:
                    gb, _ = groups[-1]
                    self._remove_multi_group(base_name, gb, self.form)
                for i, group_dict in enumerate(group_values):
                    if i >= len(self.multi_param_groups[base_name]):
                        self._add_multi_group(base_name, label, fields, required, self.form)
                    groupbox, vbox = self.multi_param_groups[base_name][i]
                    for j in range(vbox.rowCount()):
                        item = vbox.itemAt(j, FieldRole)
                        if item is not None and item.widget() is not None:
                            # Todo: make this work for any type of widget
                            w = item.widget()
                            varname = self.widget_to_varname.get(w)
                            if varname and varname in group_dict:
                                val = group_dict[varname]
                                self._set_widget_value(w, val)
        except Exception as e:
            QMessageBox.warning(self, "Import Error", str(e))
            logger.warning(f"Import Error: {e}")

    def export_params(self, file_path = None):
        try:
            params = self.get_params(includeBaseParams=False) # excluse base parameters
            # Add module name
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
            # cooldown is not user-editable, but always included in params
            self.params['cooldown'] = self.cooldown
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

    def _param_def_to_dict(self, param):
        # Returns dict with keys: name, label, typ, required, placeholder
        if len(param) == 5:
            name, label, typ, required, placeholder = param
        else:
            name, label, typ, required = param
            placeholder = None
        return dict(name=name, label=label, typ=typ, required=required, placeholder=placeholder) 