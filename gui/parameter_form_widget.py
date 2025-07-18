import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QPushButton,
                             QLineEdit, QComboBox, QCheckBox, QLabel, QMessageBox)
from logger import get_logger

logger = get_logger(__name__)

# FieldRole and LabelRole constants for QFormLayout
FieldRole = 1  # QFormLayout.FieldRole
LabelRole = 0  # QFormLayout.LabelRole


MULTI_VALUE_GOES_IN_GROUPBOX = True

class ParameterFormWidget(QWidget):
    """
    A reusable widget that dynamically generates a form from a parameter definition list.
    Supports simple fields, multi-value fields, and arbitrarily nested groups.
    """

    def __init__(self, param_defs, data_columns=None, parent=None):
        super().__init__(parent)
        self.param_defs = param_defs
        self.data_columns = data_columns or []

        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        form_layout = QFormLayout()
        self.main_layout.addLayout(form_layout)
        self._build_form_from_defs(self.param_defs, form_layout)

    def _param_def_to_dict(self, param):
        """Converts a parameter tuple to a dictionary for easier access."""
        # Ensure the tuple has 5 elements, adding None for placeholder if missing.
        p_normalized = param if len(param) == 5 else (*param, None)
        name, label, typ, required, placeholder = p_normalized
        return dict(name=name, label=label, typ=typ, required=required, placeholder=placeholder)

    def _build_form_from_defs(self, param_defs, parent_layout):
        """Recursively builds the UI from a list of parameter definitions."""
        for param_tuple in param_defs:
            # Normalize the definition at the point of use to ensure it's always 5 elements.
            d = self._param_def_to_dict(param_tuple)
            name, label, typ, required, placeholder = d['name'], d['label'], d['typ'], d['required'], d['placeholder']

            rlabel = f"{label} *" if required else label
            m = re.match(r'(.+)_%d$', name) if name else None

            # --- Unified Group Logic (for multi-groups and single groups) ---
            if isinstance(typ, dict) and 'fields' in typ:
                is_multi = bool(m)
                base_name = m.group(1) if is_multi else name

                if is_multi:
                    # Create a main container QGroupBox for the repeatable groups.
                    # This groupbox will span the full width of the form.
                    container_group = QGroupBox(rlabel)
                    container_group.setProperty('is_multi_group_container', True)
                    container_group.setProperty('param_name', base_name)

                    # The layout inside this container will hold the individual group instances.
                    container_layout = QVBoxLayout(container_group)
                    container_layout.setContentsMargins(5, 5, 5, 5)

                    # Add the main container to the parent form layout.
                    parent_layout.addRow(container_group)

                    # Add the first instance of the repeatable group into the container's layout.
                    self._add_group_instance(container_layout, base_name, label, typ['fields'], required, is_multi)
                else:  # Single, static group
                    groupbox = QGroupBox(rlabel)
                    groupbox.setProperty('is_static_group', True)
                    groupbox.setProperty('param_name', base_name)
                    form_layout = QFormLayout()
                    groupbox.setLayout(form_layout)
                    parent_layout.addRow(groupbox)
                    # Recursively build the form for the fields inside this single group
                    self._build_form_from_defs(typ['fields'], form_layout)
                continue

            # --- Multi-Value (for simple, repeatable parameters) ---
            elif m:
                base_name = m.group(1)
                self._create_multi_value_ui(parent_layout, base_name, rlabel, typ, required, placeholder)
                continue

            # --- Simple Parameter ---
            w = self._make_widget_for_type(typ, placeholder, required)
            w.setProperty('param_name', name)
            parent_layout.addRow(rlabel, w)

    def _create_multi_value_ui(self, parent_layout, base_name, rlabel, typ, required, placeholder):
        """Creates a UI for repeatable single-value parameters with add/remove buttons on each row."""

        container_widget = QGroupBox(rlabel) if MULTI_VALUE_GOES_IN_GROUPBOX else QWidget()
        # This layout will hold all the individual rows for this parameter.
        container_layout = QVBoxLayout(container_widget)
        if not MULTI_VALUE_GOES_IN_GROUPBOX:
            container_layout.setContentsMargins(0, 0, 0, 0)
        container_widget.setProperty('is_multi_value_container', True)
        container_widget.setProperty('param_name', base_name)

        def add_row(insert_pos=-1):
            """Internal function to create and add a single parameter row."""
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Create the main input widget for the row
            input_widget = self._make_widget_for_type(typ, placeholder, required)
            input_widget.setProperty('param_name', f"{base_name}_item")  # Mark as item

            # Create buttons
            add_btn = QPushButton('+')
            remove_btn = QPushButton('–')
            add_btn.setToolTip("Add new item below")
            remove_btn.setToolTip("Remove this item")
            add_btn.setMaximumWidth(36)
            remove_btn.setMaximumWidth(36)

            # Add widgets to row layout
            row_layout.addWidget(input_widget)
            row_layout.addWidget(add_btn)
            row_layout.addWidget(remove_btn)

            # Insert the completed row widget into the main container
            if insert_pos == -1:
                container_layout.addWidget(row_widget)
            else:
                container_layout.insertWidget(insert_pos, row_widget)

            # --- Connect Signals ---
            # Use a lambda to capture the specific row_widget we need to act on
            add_btn.clicked.connect(lambda: add_row_after(row_widget))
            remove_btn.clicked.connect(lambda: remove_row(row_widget))

        def add_row_after(current_row_widget):
            """Finds the index of the current row and adds a new one after it."""
            index = container_layout.indexOf(current_row_widget)
            if index != -1:
                add_row(insert_pos=index + 1)

        def remove_row(row_to_remove):
            """Removes a specific row from the layout."""
            # Don't remove the last row if the parameter is required
            if required and container_layout.count() <= 1:
                QMessageBox.warning(self, "Cannot Remove", "At least one value is required for this field.")
                return

            # Remove from layout and delete the widget
            container_layout.removeWidget(row_to_remove)
            row_to_remove.deleteLater()

            # If the last row was removed, add a fresh one back
            if not required and container_layout.count() == 0:
                add_row()

        # Add the whole container to the main form and add the first row
        if MULTI_VALUE_GOES_IN_GROUPBOX:
            parent_layout.addRow(container_widget)
        else:
            parent_layout.addRow(rlabel, container_widget)
        add_row()

    def _add_group_instance(self, parent_layout, base_name, label, fields, required, is_multi, insert_pos=None):
        """Adds a single instance of a parameter group."""
        groupbox = QGroupBox()
        groupbox.setProperty('is_group_instance', True)
        group_vbox = QVBoxLayout(groupbox)
        param_form = QFormLayout()
        group_vbox.addLayout(param_form)

        # Recursively build the form for the fields inside this group instance
        self._build_form_from_defs(fields, param_form)

        if is_multi:
            # Add the control bar for repeatable groups
            btn_bar_layout = QHBoxLayout()
            add_above_btn = QPushButton("Add Above")
            remove_btn = QPushButton("Remove")
            add_below_btn = QPushButton("Add Below")

            btn_bar_layout.addStretch()
            btn_bar_layout.addWidget(add_above_btn)
            btn_bar_layout.addWidget(remove_btn)
            btn_bar_layout.addWidget(add_below_btn)
            btn_bar_layout.addStretch()
            group_vbox.addLayout(btn_bar_layout)

            # Connect signals, capturing the specific groupbox instance to act upon
            add_above_btn.clicked.connect(
                lambda _, b=base_name, gb=groupbox: self._handle_multi_group_action('add_above', b, gb, label, fields,
                                                                                    required))
            remove_btn.clicked.connect(
                lambda _, b=base_name, gb=groupbox: self._handle_multi_group_action('remove', b, gb, label, fields,
                                                                                    required))
            add_below_btn.clicked.connect(
                lambda _, b=base_name, gb=groupbox: self._handle_multi_group_action('add_below', b, gb, label, fields,
                                                                                    required))

        # Insert the new groupbox into its parent container's layout
        if insert_pos is None:
            insert_pos = parent_layout.count()
        parent_layout.insertWidget(insert_pos, groupbox)

        if is_multi:
            self._update_multi_group_titles(parent_layout, label, required)

    def _handle_multi_group_action(self, action, base_name, groupbox_ref, label, fields, required):
        """Handles add/remove actions for repeatable groups."""
        container_widget = groupbox_ref.parentWidget()
        parent_layout = container_widget.layout()
        if not parent_layout: return

        # Find the index of the groupbox that triggered the action
        current_index = -1
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item and item.widget() == groupbox_ref:
                current_index = i
                break
        if current_index == -1: return

        if action == 'remove':
            if required and parent_layout.count() <= 1:
                QMessageBox.warning(self, "Cannot Remove", "At least one group is required for this parameter.")
                return
            # We need to remove the widget from the layout before deleting it
            item = parent_layout.takeAt(current_index)
            if item and item.widget(): # Note: item.widget() == groupbox_ref and should be deleted as well.
                item.widget().deleteLater()
            self._update_multi_group_titles(parent_layout, label, required)

            if not required and parent_layout.count() == 0:
                # TODO: add a plus button here instead and remove it later
                self._add_group_instance(parent_layout, base_name, label, fields, required, is_multi=True)
        elif action == 'add_above':
            self._add_group_instance(parent_layout, base_name, label, fields, required, is_multi=True,
                                     insert_pos=current_index)
        elif action == 'add_below':
            self._add_group_instance(parent_layout, base_name, label, fields, required, is_multi=True,
                                     insert_pos=current_index + 1)

    def _update_multi_group_titles(self, parent_layout, label, required):
        """Updates the titles of all groups in a multi-group list to be numbered correctly."""
        group_idx = 0
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item and isinstance(item.widget(), QGroupBox):
                label_text = f"{label} {group_idx + 1}" + (" *" if required else "")
                item.widget().setTitle(label_text)
                group_idx += 1

    def _make_widget_for_type(self, typ, placeholder=None, required=True):
        """Creates the appropriate QWidget for a given parameter type."""
        if isinstance(typ, (tuple, list)):
            w = QComboBox()
            if not required: w.addItem("")
            w.addItems([str(v) for v in typ])
        elif typ == 'dropdown_column':
            w = QComboBox()
            if not required: w.addItem("")
            w.addItems(self.data_columns)
        elif typ == 'checkbox' or typ == bool:
            w = QCheckBox()
        else:
            w = QLineEdit()

        # Store definition info directly on the widget for later retrieval
        w.setProperty('typ', typ)
        w.setProperty('placeholder', placeholder)
        w.setProperty('required', required)

        if placeholder and hasattr(w, 'setPlaceholderText') and typ not in ('label', 'checkbox'):
            w.setPlaceholderText(str(placeholder))
        if typ in [bool, 'checkbox'] and placeholder is not None:
            w.setChecked(bool(placeholder))
        return w

    def get_params(self):
        """Recursively collects and returns all parameters from the form as a dictionary."""
        top_level_layout = self.main_layout.itemAt(0).layout()
        return self._collect_params_from_layout(top_level_layout)

    def _collect_params_from_layout(self, layout):
        """Helper function to recursively traverse layouts and collect parameter values."""
        params = {}
        if not layout: return params

        # This handles both QFormLayout and other layouts like QVBoxLayout
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item: continue

            widget = item.widget()
            if not widget:
                # If the item is a layout, recurse into it
                if item.layout():
                    nested_params = self._collect_params_from_layout(item.layout())
                    params.update(nested_params)
                continue

            # Handle QFormLayout rows specifically
            if isinstance(layout, QFormLayout):
                label_item = layout.itemAt(i, LabelRole)
                field_item = layout.itemAt(i, FieldRole)
                spanning_item = layout.itemAt(i, QFormLayout.SpanningRole)

                if field_item:
                    widget = field_item.widget()
                elif spanning_item:
                    widget = spanning_item.widget()
                else:
                    continue  # Skip labels or empty rows

            if not widget: continue

            param_name = widget.property('param_name')
            if not param_name: continue

            if widget.property('is_multi_group_container'):
                # Collect from a list of repeatable groups
                group_values = []
                container_layout = widget.layout()
                for j in range(container_layout.count()):
                    item = container_layout.itemAt(j)
                    if item and isinstance(item.widget(), QGroupBox):
                        group_box = item.widget()
                        # The first item in the group's QVBoxLayout is the QFormLayout
                        form_layout = group_box.layout().itemAt(0).layout()
                        group_values.append(self._collect_params_from_layout(form_layout))
                params[param_name] = group_values
            elif widget.property('is_static_group'):
                # Collect from a single static group
                form_layout = widget.layout()
                params[param_name] = self._collect_params_from_layout(form_layout)
            elif widget.property('is_multi_value_container'):
                # Collect from a simple multi-value container
                values = []
                container_layout = widget.layout()
                for j in range(container_layout.count()):
                    row_widget_item = container_layout.itemAt(j)
                    # The item is a row widget
                    if row_widget_item and row_widget_item.widget():
                        row_widget = row_widget_item.widget()
                        row_layout = row_widget.layout()
                        # The first widget in the row's layout is the input widget
                        if row_layout and row_layout.count() > 0:
                            input_item = row_layout.itemAt(0)
                            if input_item and input_item.widget():
                                w = input_item.widget()
                                typ = w.property('typ')
                                v = self._get_widget_value(w, typ)
                                if v is not None and v != "":
                                    values.append(v)
                params[param_name] = values
            else:
                # Collect from a simple widget
                typ = widget.property('typ')
                params[param_name] = self._get_widget_value(widget, typ)

        return params

    def _get_widget_value(self, w, typ):
        """Retrieves the value from a widget, casting it to its original type if possible."""
        if isinstance(w, QCheckBox): return w.isChecked()
        if isinstance(w, QComboBox): return w.currentText()
        if isinstance(w, QLineEdit):
            val = w.text()
            if isinstance(typ, type) and typ is not str:
                try:
                    return typ(val)
                except (ValueError, TypeError):
                    return val  # Return as string on failure
            return val
        if hasattr(w, 'text'): return w.text()
        return None

    def validate(self):
        """Validates all required fields in the form, raising ValueError on failure."""
        params = self.get_params()
        # This validation needs to be recursive to handle nested required fields.
        # For now, we'll keep the top-level validation.
        for p_def in self.param_defs:
            d = self._param_def_to_dict(p_def)
            if d.get('required'):
                name = d['name']
                base_name = name.split('_%d')[0] if name else None
                if not base_name: continue

                label = d.get('label')
                val = params.get(base_name)

                if val is None or val == "" or val == []:
                    raise ValueError(f"Required parameter '{label}' is missing.")
        return True


    def set_params(self, params):
        """Populates the form with values from a dictionary."""
        # NOTE: This is a complex operation due to the dynamic nature of the form,
        # especially for multi-value and multi-group fields which require adding/removing
        # widgets to match the data. A full implementation would mirror the `import_params`
        # logic from the original ProcessingDialog, which is beyond this refactor's scope.
        logger.warning("set_params() is not fully implemented for dynamic forms.")
        # Basic implementation for simple, top-level fields:
        top_level_layout = self.main_layout.itemAt(0).layout()
        for i in range(top_level_layout.rowCount()):
            field_item = top_level_layout.itemAt(i, FieldRole)
            if field_item and field_item.widget():
                w = field_item.widget()
                name = w.property('param_name')
                if name in params:
                    self._set_widget_value(w, params[name])

    def _set_widget_value(self, w, value):
        """Sets the value of a widget."""
        if value is None: return
        if isinstance(w, QComboBox):
            idx = w.findText(str(value))
            if idx >= 0: w.setCurrentIndex(idx)
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(value))
        elif isinstance(w, QLineEdit):
            w.setText(str(value))
        else:
            print(f"Could not set widget value with type {type(w)}", value)
