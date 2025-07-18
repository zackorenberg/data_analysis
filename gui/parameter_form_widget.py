import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QPushButton,
                             QLineEdit, QComboBox, QCheckBox, QLabel, QMessageBox)
from logger import get_logger

logger = get_logger(__name__)

# FieldRole and LabelRole constants for QFormLayout
FieldRole = 1  # QFormLayout.FieldRole
LabelRole = 0  # QFormLayout.LabelRole


MULTI_VALUE_GOES_IN_GROUPBOX = True

PROPERTY_MULTI_VALUE = 'is_multi_value_container'
PROPERTY_MULTI_GROUP = 'is_multi_group_container'
PROPERTY_GROUP = 'is_group_container'

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

    def _validate_type_dict(self, type_dict, is_multi = False):
        """
        This should have all the necessary stuff to validate a dictionary type

        Currently, it is just in _build_form_from_defs
        """
        pass


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

                if not is_multi and typ.get('type') == 'multi':
                    logger.warning("Deprication warning: Use of 'type: multi' without internal name suffix '_%d' is deprecated.")
                    is_multi = True
                elif is_multi and typ.get('type') == 'group':
                    logger.warning("Deprication warning: Use of 'type: group' with internal name suffix '_%d' is deprecated, please use 'type: multi' instead.")
                    is_multi = False

                if is_multi:
                    # Create a main container QGroupBox for the repeatable groups.
                    # This groupbox will span the full width of the form.
                    container_group = QGroupBox(rlabel)
                    container_group.setProperty(PROPERTY_MULTI_GROUP, True)
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
                    groupbox.setProperty(PROPERTY_GROUP, True)
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
            w = self._make_widget_for_type(*param_tuple)
            parent_layout.addRow(rlabel, w)

    def _create_multi_value_ui(self, parent_layout, base_name, rlabel, typ, required, placeholder, values = None):
        """Creates a UI for repeatable single-value parameters with add/remove buttons on each row."""

        container_widget = QGroupBox(rlabel) if MULTI_VALUE_GOES_IN_GROUPBOX else QWidget()
        # This layout will hold all the individual rows for this parameter.
        container_layout = QVBoxLayout(container_widget)
        if not MULTI_VALUE_GOES_IN_GROUPBOX:
            container_layout.setContentsMargins(0, 0, 0, 0)
        container_widget.setProperty(PROPERTY_MULTI_VALUE, True)
        container_widget.setProperty('param_name', base_name)
        container_widget.setProperty('label', rlabel)
        container_widget.setProperty('typ', typ)
        container_widget.setProperty('required', required)
        container_widget.setProperty('placeholder', placeholder)


        def add_row(insert_pos=-1):
            """Internal function to create and add a single parameter row."""
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Create the main input widget for the row
            input_widget = self._make_widget_for_type(f"{base_name}_item", rlabel, typ, required, placeholder)
            # input_widget.setProperty('param_name', f"{base_name}_item")  # Mark as item

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

            return input_widget  # This is for if we want to set the value later

        def add_row_after(current_row_widget):
            """Finds the index of the current row and adds a new one after it."""
            index = container_layout.indexOf(current_row_widget)
            if index != -1:
                return add_row(insert_pos=index + 1)

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

        container_widget.setProperty('add_row', add_row)
        container_widget.setProperty('add_row_after', add_row_after)
        container_widget.setProperty('remove_row', remove_row)
        if values:
            for value in values:
                w = add_row()
                self._set_widget_value(w, value)
        else:
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
                lambda _, b=base_name, gb=groupbox: self._handle_multi_group_action('add_above', b, gb, label, fields, required)
            )
            remove_btn.clicked.connect(
                lambda _, b=base_name, gb=groupbox: self._handle_multi_group_action('remove', b, gb, label, fields, required)
            )
            add_below_btn.clicked.connect(
                lambda _, b=base_name, gb=groupbox: self._handle_multi_group_action('add_below', b, gb, label, fields, required)
            )

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
            # We need to remove the widget from the layout before deleting it so it registers when we re-title
            item = parent_layout.takeAt(current_index)
            if item and item.widget(): # Note: item.widget() == groupbox_ref and should be deleted as well.
                item.widget().deleteLater()
            self._update_multi_group_titles(parent_layout, label, required)

            if not required and parent_layout.count() == 0:
                # TODO: add a plus button here instead and remove it later
                self._add_group_instance(parent_layout, base_name, label, fields, required, is_multi=True)
        elif action == 'add_above':
            self._add_group_instance(parent_layout, base_name, label, fields, required, is_multi=True, insert_pos=current_index)
        elif action == 'add_below':
            self._add_group_instance(parent_layout, base_name, label, fields, required, is_multi=True, insert_pos=current_index + 1)

    def _update_multi_group_titles(self, parent_layout, label, required):
        """Updates the titles of all groups in a multi-group list to be numbered correctly."""
        group_idx = 0
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item and isinstance(item.widget(), QGroupBox):
                label_text = f"{label} {group_idx + 1}" + (" *" if required else "")
                item.widget().setTitle(label_text)
                group_idx += 1

    def _make_widget_for_type(self, name, label, typ, required, placeholder=None):
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
        elif typ == 'label':
            w = QLabel()
        else:
            w = QLineEdit()

        # Store definition info directly on the widget for later retrieval
        w.setProperty('param_name', name)
        w.setProperty('label', label)
        w.setProperty('typ', typ)
        w.setProperty('placeholder', placeholder)
        w.setProperty('required', required)

        if placeholder and hasattr(w, 'setPlaceholderText') and typ not in ('label', 'checkbox', bool):
            w.setPlaceholderText(str(placeholder))

        # Label and bool types
        if placeholder and typ == 'label':
            w.setText(placeholder)
        if typ in [bool, 'checkbox'] and placeholder is not None:
            w.setChecked(bool(placeholder))

        # Add tooltip if type is required
        if isinstance(typ, type) and typ not in [str, bool]:
            w.setToolTip(f"{typ.__name__} value required.")
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

            if widget.property(PROPERTY_MULTI_GROUP):
                # Collect from a list of repeatable groups
                group_values = []
                container_layout = widget.layout()
                for j in range(container_layout.count()):
                    item = container_layout.itemAt(j)
                    if item and isinstance(item.widget(), QGroupBox):
                        group_box = item.widget()
                        # The first item in the group's QVBoxLayout is the QFormLayout
                        form_layout = group_box.layout().itemAt(0).layout()
                        v = self._collect_params_from_layout(form_layout)
                        if v:
                            group_values.append(v)
                params[param_name] = group_values
            elif widget.property(PROPERTY_GROUP):
                # Collect from a single static group
                form_layout = widget.layout()
                params[param_name] = self._collect_params_from_layout(form_layout)
            elif widget.property(PROPERTY_MULTI_VALUE):
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
                v = self._get_widget_value(widget, typ)
                if v is not None and v != '':
                    params[param_name] = v

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
                    logger.warning(f"Could not cast widget value '{w.property('param_name')}' with value '{val}' to type '{typ}'.")
                    return val  # Return as string on failure
            return val
        if hasattr(w, 'text'): return w.text()
        return None

    def validate(self):
        """
        Recursively validates all required fields in the form, raising ValueError on failure.
        Handles nested fields and conditional requirements within multi-groups.
        """
        params_data = self.get_params()
        self._validate_recursive(self.param_defs, params_data)
        return True  # If no exception was raised, validation passed

    def _validate_recursive(self, param_defs, params_data):
        """
        A recursive helper to validate a set of parameter definitions against
        a dictionary of collected data.
        """
        for p_def in param_defs:
            d = self._param_def_to_dict(p_def)
            name = d.get('name')
            label = d.get('label')
            typ = d.get('typ')
            is_required = d.get('required')

            if not name:
                continue

            # TODO: REWRITE THIS LOGIC!!!
            is_multi_group = isinstance(typ, dict) and 'fields' in typ and (name.endswith('_%d') or typ.get('type') == 'multi')
            is_group = isinstance(typ, dict) and 'fields' in typ and (not name.endswith('_%d') or typ.get('type') == 'group')
            is_multi_value = not isinstance(typ, dict) and name.endswith('_%d')

            base_name = name.split('_%d')[0]
            value = params_data.get(base_name)

            # --- Validation Logic ---

            # Normal field (check value)
            if not (is_multi_group or is_group or is_multi_value):
                if value is None or value == '': # If there is a value
                    # Required fields must have a value
                    if is_required:
                        raise ValueError(f"Required parameter '{label}' is missing.")
                else:
                    # Field type must be correctly castable
                    if isinstance(typ, type) and typ is not str:
                        try:
                            typ(value)
                        except ValueError as e:
                            raise ValueError(f"Field '{label}' must be of type '{typ.__name__}': {e}")

            # Required multi-value or multi-group list cannot be empty. Putting static group for consistency
            if (is_multi_value or is_multi_group or is_group) and is_required:
                if not value:  # Handles None or empty list []
                    raise ValueError(f"At least one entry is required for '{label}'.")

            ######## Recurse for groups/lists #########

            # type: multi value
            if is_multi_value and value:
                if isinstance(value, list):
                    if isinstance(typ, type) and typ is not str:
                        for i, v in enumerate(value):
                            try:
                                typ(v)
                            except ValueError as e:
                                raise ValueError(f"Field '{label} {i+1}' must be of type '{typ.__name__}': {e}")
                else:
                    logger.warning(f"Unexpected value type for type multi value: {type(value).__name__}")

            # type: group
            if is_group and value:
                if isinstance(value, dict):
                    # Recursively validate the fields within group. Children requirements are enforced fully
                    self._validate_recursive(typ['fields'], value)
                else:
                    logger.warning(f"Data for group '{label}' is not a dictionary. Skipping validation.")

            # type: multi group
            if is_multi_group and value:
                if isinstance(value, list):
                    # Regardless of whether multi groups are required, requirements of children are enforced
                    for i, group_instance_data in enumerate(value):
                        try:
                            self._validate_recursive(typ['fields'], group_instance_data)
                        except ValueError as e:
                            raise ValueError(f"Error in '{label} {i + 1}': {e}")
                else:
                    logger.warning(f"Data for multi-group '{label}' is not a list. Skipping validation.")


    def set_params(self, params):
        """
        Populates the form with values from a dictionary. This method will clear and
        recreate dynamic parts of the form (multi-value, multi-group) to match the
        provided data structure.
        """
        if not isinstance(params, dict):
            logger.error("set_params expects a dictionary.")
            return

        logger.debug(f"Setting parameters in form: {params}")
        top_level_layout = self.main_layout.itemAt(0).layout()
        self._set_params_in_layout(top_level_layout, params)

    def _set_params_in_layout(self, layout, params, param_defs = None):
        """
        Recursively traverses a layout, finds widgets by their 'param_name' property,
        and sets their values from the params dictionary.
        """
        if not param_defs:
            param_defs = self.param_defs

        if not layout or not params:
            return

        # Iterate through all widgets in the layout to find ones with a 'param_name'
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item: continue

            widget = None
            # Determine the actual widget to process for this layout item
            if isinstance(layout, QFormLayout):
                # For QFormLayout, the widget is in the FieldRole or SpanningRole
                field_item = layout.itemAt(i, QFormLayout.FieldRole)
                spanning_item = layout.itemAt(i, QFormLayout.SpanningRole)
                if field_item and field_item.widget():
                    widget = field_item.widget()
                elif spanning_item and spanning_item.widget():
                    widget = spanning_item.widget()
            else:
                # For other layouts (QVBoxLayout, etc.), the item is the widget
                widget = item.widget()

            if not widget:
                # It might be a nested layout without being a QGroupBox. Recurse if so.
                if item.layout():
                    self._set_params_in_layout(item.layout(), params, param_defs)
                continue

            param_name = widget.property('param_name')
            if not param_name:
                logger.warning("Could not find parameter name for widget in layout: {widget}")
                continue
            if param_name not in params: # Value was not saved
                continue

            value = params[param_name]

            # --- Dispatch to the correct handler based on widget type ---
            if widget.property(PROPERTY_MULTI_GROUP):
                self._set_multi_group_params(widget, value, param_defs)
            elif widget.property(PROPERTY_GROUP):
                if isinstance(value, dict):
                    self._set_params_in_layout(widget.layout(), value)
            elif widget.property(PROPERTY_MULTI_VALUE):
                self._set_multi_value_params(widget, value)
            else:
                # This is a simple, single-value widget, so we set the value
                self._set_widget_value(widget, value)
                # Note: properties should already be set as we did not create any widgets

    def _set_multi_group_params(self, container_group, group_values, param_defs=None):
        """
        Clears and repopulates a multi-group container based on a list of dictionaries.
        """
        if not param_defs:
            param_defs = self.param_defs

        if not isinstance(group_values, list):
            logger.warning(
                f"Expected a list for multi-group '{container_group.property('param_name')}', got {type(group_values)}.")
            return

        container_layout = container_group.layout()
        # Clear existing group instances
        while container_layout.count():
            item = container_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Find the original parameter definition to get the fields
        base_name = container_group.property('param_name')

        import pprint
        print('+'*20)
        print(base_name)
        pprint.pprint(param_defs)

        param_def = next(
            (p for p in param_defs if self._param_def_to_dict(p).get('name', '').startswith(base_name)), None)

        if not param_def:
            logger.error(f"Could not find parameter definition for multi-group '{base_name}'.")
            return


        d = self._param_def_to_dict(param_def)
        label, fields, required = d['label'], d['typ']['fields'], d['required']
        # Add a new group instance for each dictionary in the list
        for single_group_params in group_values:
            self._add_group_instance(container_layout, base_name, label, fields, required, is_multi=True)
            new_groupbox = container_layout.itemAt(container_layout.count() - 1).widget()
            print("="*20)
            print(label)
            pprint.pprint(single_group_params)
            pprint.pprint(fields)
            if new_groupbox and isinstance(single_group_params, dict):
                form_layout = new_groupbox.layout().itemAt(0).layout()
                self._set_params_in_layout(form_layout, single_group_params, param_defs = fields)

    def _set_multi_value_params(self, container_widget, values):
        """
        Clears and repopulates a multi-value container based on a list of values.
        """
        if not isinstance(values, list):
            logger.warning(f"Expected a list for multi-value '{container_widget.property('param_name')}', got {type(values)}.")
            return

        container_layout = container_widget.layout()
        # Clear existing row widgets
        while container_layout.count():
            item = container_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        add_row = container_widget.property('add_row')
        if add_row:
            for value in values:
                w = add_row()
                self._set_widget_value(w, value)
        else:
            logger.error("Cannot find add_row() function.")


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
            logger.error(f"Could not set widget value with type '{type(w)}' and value '{value}'")
