from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QFormLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QWidget, QGroupBox
from PyQt5.QtCore import Qt
import json
import os
from DataManagement.module_loader import discover_modules
from processing_base import BasePreprocessingModule, BasePostprocessingModule
import re
from localvars import PROCESSING_MODULES_DIR

# FieldRole and LabelRole constants for QFormLayout
FieldRole = 1  # QFormLayout.FieldRole
LabelRole = 0  # QFormLayout.LabelRole

class ProcessingDialog(QDialog):
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
        self._init_ui()

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
        # Parameter form
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
        self.multi_param_widgets = {}  # base_name: [widgets]
        self.multi_param_groups = {}   # base_name: groupbox
        self.widget_to_varname = {}   # widget: varname for multi-groups
        if idx < 0 or idx >= len(self.modules):
            return
        _, cls, parameters = self.modules[idx]
        self.selected_module = cls
        self._build_param_form(parameters, self.form)

    def _build_param_form(self, parameters, parent_layout, parent_base=None):
        for param in parameters:
            if isinstance(param, dict):
                continue
            name, label, typ, required = param
            m = re.match(r'(.+)_%d$', name)
            if m:
                base_name = m.group(1) if not parent_base else f"{parent_base}.{m.group(1)}"
                if isinstance(typ, dict) and typ.get('type') == 'multi':
                    if base_name not in self.multi_param_groups:
                        self.multi_param_groups[base_name] = []
                        self._add_multi_group(base_name, label, typ['fields'], required, parent_layout)
                    continue
                else:
                    if base_name not in self.multi_param_widgets:
                        self.multi_param_widgets[base_name] = []
                        self._add_multi_param_row(base_name, label, typ, required, parent_layout)
                    continue
            if isinstance(typ, dict) and typ.get('type') == 'multi':
                base_name = name if not parent_base else f"{parent_base}.{name}"
                if base_name not in self.multi_param_groups:
                    self.multi_param_groups[base_name] = []
                    self._add_multi_group(base_name, label, typ['fields'], required, parent_layout)
                continue
            w = self._make_widget_for_type(typ)
            parent_layout.addRow(label + (" *" if required else ""), w)
            self.param_widgets[name if not parent_base else f"{parent_base}.{name}"] = w
            # For multi-groups, track varname for widgets
            if parent_base:
                self.widget_to_varname[w] = name

    def _make_widget_for_type(self, typ):
        if isinstance(typ, (tuple, list)):
            w = QComboBox()
            w.addItems([str(v) for v in typ])
        elif typ == 'dropdown_column':
            w = QComboBox()
            w.addItems(self.data_columns)
        elif typ == 'dropdown':
            w = QComboBox()
            w.addItems(self.data_columns)
        else:
            w = QLineEdit()
        return w

    def _add_multi_param_row(self, base_name, label, typ, required, parent_layout, insert_after=None):
        def add_row(after_idx=None):
            w = self._make_widget_for_type(typ)
            row_layout = QHBoxLayout()
            row_layout.addWidget(w)
            minus_btn = QPushButton("–")
            plus_btn = QPushButton("+")
            row_layout.addWidget(plus_btn)
            row_layout.addWidget(minus_btn)
            container = QWidget()
            container.setLayout(row_layout)
            # Determine index for insertion
            if after_idx is None:
                idx = len(self.multi_param_widgets[base_name])
            else:
                idx = after_idx + 1
            # Insert in widgets list and layout
            self.multi_param_widgets[base_name].insert(idx, (w, container))
            # Insert in layout at correct position
            label_text = f"{label} {idx+1}" + (" *" if required else "")
            parent_layout.insertRow(idx, label_text, container)
            # Connect buttons
            plus_btn.clicked.connect(lambda: add_row(idx))
            minus_btn.clicked.connect(lambda: self._remove_multi_param_row(base_name, container, parent_layout))
            self._update_multi_param_labels(base_name, parent_layout, label, required)
        add_row(insert_after)

    def _remove_multi_param_row(self, base_name, container, parent_layout):
        for i, (w, cont) in enumerate(self.multi_param_widgets[base_name]):
            if cont == container:
                parent_layout.removeRow(cont)
                self.multi_param_widgets[base_name].pop(i)
                break
        self._update_multi_param_labels(base_name, parent_layout)

    def _update_multi_param_labels(self, base_name, parent_layout, label=None, required=None):
        # Update numbering for all rows
        for idx, (w, cont) in enumerate(self.multi_param_widgets[base_name]):
            row = parent_layout.getLayoutPosition(cont)[0]
            if label is not None:
                label_text = f"{label} {idx+1}" + (" *" if required else "")
            else:
                # Try to get label from the layout
                label_text = parent_layout.itemAt(row, LabelRole).widget().text().split(' ')[0] + f" {idx+1}"
            if parent_layout.itemAt(row, LabelRole) and parent_layout.itemAt(row, LabelRole).widget():
                parent_layout.itemAt(row, LabelRole).widget().setText(label_text)

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
            self._build_param_form(fields, vbox, parent_base=base_name)
            # Determine index for insertion
            if after_idx is None:
                idx = len(self.multi_param_groups[base_name])
            else:
                idx = after_idx + 1
            self.multi_param_groups[base_name].insert(idx, (groupbox, vbox))
            label_text = f"{label} {idx+1}" + (" *" if required else "")
            groupbox.setTitle(label_text)
            parent_layout.insertRow(idx, groupbox)
            plus_btn.clicked.connect(lambda: add_group(idx))
            minus_btn.clicked.connect(lambda: self._remove_multi_group(base_name, groupbox, parent_layout))
            self._update_multi_group_labels(base_name, parent_layout, label, required)
            # For all widgets in vbox, track their varnames
            for subparam in fields:
                subname, _, _, _ = subparam
                key = f"{base_name}.{subname}"
                w = self.param_widgets.get(key)
                if w:
                    self.widget_to_varname[w] = subname
        add_group(insert_after)

    def _remove_multi_group(self, base_name, groupbox, parent_layout):
        for i, (gb, vbox) in enumerate(self.multi_param_groups[base_name]):
            if gb == groupbox:
                parent_layout.removeRow(gb)
                self.multi_param_groups[base_name].pop(i)
                break
        self._update_multi_group_labels(base_name, parent_layout)

    def _update_multi_group_labels(self, base_name, parent_layout, label=None, required=None):
        for idx, (gb, vbox) in enumerate(self.multi_param_groups[base_name]):
            label_text = f"{label} {idx+1}" + (" *" if required else "")
            gb.setTitle(label_text)

    def get_params(self):
        params = {}
        idx = self.module_combo.currentIndex()
        _, _, parameters = self.modules[idx]
        # Handle multi-value params
        for base_name, widgets in getattr(self, 'multi_param_widgets', {}).items():
            values = []
            for w, _ in widgets:
                val = w.currentText() if isinstance(w, QComboBox) else w.text()
                if val:
                    values.append(val)
            params[base_name] = values
        # Handle multi-groups
        for base_name, groups in getattr(self, 'multi_param_groups', {}).items():
            group_values = []
            for groupbox, vbox in groups:
                group_params = {}
                # Find all widgets in this group
                for i in range(vbox.rowCount()):
                    item = vbox.itemAt(i, FieldRole)
                    if item is not None and item.widget() is not None:
                        w = item.widget()
                        varname = self.widget_to_varname.get(w)
                        if not varname:
                            continue
                        if isinstance(w, QComboBox):
                            val = w.currentText()
                        else:
                            val = w.text()
                        if val:
                            group_params[varname] = val
                group_values.append(group_params)
            params[base_name] = group_values
        # Handle regular params
        for name, label, typ, required in parameters:
            m = re.match(r'(.+)_%d$', name)
            if m:
                continue  # already handled
            if isinstance(typ, dict) and typ.get('type') == 'multi':
                continue  # already handled
            key = name
            w = self.param_widgets.get(key)
            if not w:
                continue
            if typ == 'dropdown' or typ == 'dropdown_column' or isinstance(typ, (tuple, list)):
                val = w.currentText()
            else:
                val = w.text()
            if required and not val:
                raise ValueError(f"Parameter '{label}' is required.")
            params[key] = val
        return params

    def import_params(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Parameters", "", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                params = json.load(f)
            for name, w in self.param_widgets.items():
                if name in params:
                    if isinstance(w, QComboBox):
                        idx = w.findText(params[name])
                        if idx >= 0:
                            w.setCurrentIndex(idx)
                    else:
                        w.setText(str(params[name]))
        except Exception as e:
            QMessageBox.warning(self, "Import Error", str(e))

    def export_params(self):
        try:
            params = self.get_params()
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Parameters", "params.json", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, 'w') as f:
                json.dump(params, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))

    def accept(self):
        try:
            self.params = self.get_params()
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "Parameter Error", str(e))

    def get_selected_module(self):
        return self.selected_module, self.params 