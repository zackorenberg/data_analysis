"""
TODO: MAKE THE EXPORTED FILE MORE EASILY READIBLE AS A "THEME" TYPE FILE, I.E SPLIT EACH LEAF INTO ITS OWN SUBDICTIONARY!
TODO: ADD NAMING/DESCRIPTION IN COMPOSER
"""

import sys
import json
import os
from PyQt5.QtWidgets import (
    QWidget, QDialog, QLayout, QSizePolicy, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QLineEdit, QLabel, QMessageBox, QApplication, QComboBox, QCheckBox, QListWidget, QListWidgetItem, QTabWidget, QFileDialog, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
import matplotlib as mpl
import cycler # dependancy for mpl
from matplotlib.rcsetup import validate_bool
from matplotlib.style.core import STYLE_BLACKLIST
import matplotlib.pyplot as plt
import re
import numpy as np
from localvars import MPL_USE_STYLE_BACKEND

from logger import get_logger
logger = get_logger(__name__)



# There is a bug in matplotlib where the rcParams['backend'] is an object instead of a string when first loading the module.
# After further investigation, it would appear the bug is due to partial initialization of the rcParams dictionary.
# This is a workaround that calls a function on rcParams that will force it to be initialized fully.
# It is worth nothing that calling plt.rcdefaults() does not actually fully initialize but rather possibly introduce a race condition on 
# application launch. Furthermore, performing an operation on rcParams causes this bug to fix even rcParamsDefault. If you don't believe me, 
# comment this out and run this file with mpl version 3.5.3
try:
    _ = mpl.rcParams['backend'] # Should be future proof, still wrapping it in a try/except just in case
except:
    pass
# Save the default rcparams for use later
default_rcparams = mpl.rcParamsDefault.copy()
# default_rcparams = mpl.rcParams.copy()
# Cache file path for just validators
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".rcparams_validators_cache.json")

def load_rcparams_cache():
    """Load rcParams cache from JSON file with version checking"""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        # Check if matplotlib version matches
        current_version = mpl.__version__
        cached_version = cache_data.get('matplotlib_version')
        
        if cached_version != current_version:
            logger.info(f"Matplotlib version changed from {cached_version} to {current_version}. Regenerating cache...")
            return None # Generates new cache automatically if None is returned
        
        return cache_data.get('validators', {})
    except Exception as e:
        logger.error(f"Error loading rcParams cache: {e}")
        return None

def save_rcparams_cache(validators):
    """Save rcParams cache to JSON file"""
    try:
        cache_data = {
            'matplotlib_version': mpl.__version__,
            'validators': validators
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        logger.info(f"rcParams cache saved to {CACHE_FILE}")
    except Exception as e:
        logger.error(f"Error saving rcParams cache: {e}")

def discover_rcparam_validators():
    """
    Helper function to discover validators for rcParams by testing with invalid values.
    Returns a dictionary mapping parameter names to their allowed values.
    """
    # Try to load from cache first
    cached_validators = load_rcparams_cache()
    if cached_validators:
        logger.info("Using cached rcParams validators")
        return cached_validators
    
    logger.info("Discovering rcParams validators...")
    validators = {}
    
    # Test each parameter with invalid values to discover validators
    for param_name in mpl.rcParams:
        test_cases = ['asdfasdfasdgad', None, object()] #test_values[param_name]
        valid_values = []
        
        for test_value in test_cases:
            try:
                # Try to set the parameter
                original_value = mpl.rcParams[param_name]
                mpl.rcParams[param_name] = test_value
                # If it succeeds, it's a valid value (but we don't want to add test values)
                # valid_values.append(test_value)  # Don't add test values
                # Restore original value
                mpl.rcParams[param_name] = original_value
            except Exception as e:
                # Extract valid values from error message
                error_msg = str(e)
                extracted_values = extract_allowed_values_from_error(error_msg)
                if extracted_values:
                    valid_values.extend(extracted_values)
                    break # we found the values no need to run further tests
                #else: # For debug purposes, to see if we missed anything
                #    if "ould not convert" not in error_msg and "does not look like" not in error_msg and "is not a valid" not in error_msg:
                #        print(f"Could not extract allowed values from error message: {error_msg}")
                # Restore original value
                mpl.rcParams[param_name] = original_value
        
        # Remove duplicates and sort
        valid_values = list(set(valid_values))
        # Convert all values to strings for consistent sorting
        valid_values = sorted([str(v) for v in valid_values])
        if valid_values:
            validators[param_name] = valid_values
    
    # Save to cache
    save_rcparams_cache(validators)
    return validators

def extract_allowed_values_from_error(error_msg):
    """Extract allowed values from validation error messages"""
    patterns = [
        r"must be one of \[(.*?)\]",
        r"must be in \[(.*?)\]", 
        r"supported values are: \[(.*?)(?:\.|$)\]",
        r"supported values are \[(.*?)(?:\.|$)\]",
        r"one of: (.*?)(?:\.|$)",
        r"allowed values are: (.*?)(?:\.|$)",
        r"valid options: (.*?)(?:\.|$)",
        r"Valid font sizes are (.*?)(?:\.|$)",
        r"is not a valid font size\. Valid font sizes are (.*?)(?:\.|$)",
        r"is not a valid font weight\. Valid font weights are (.*?)(?:\.|$)",
        r"is not a valid font style\. Valid font styles are (.*?)(?:\.|$)",
        r"is not a valid linestyle\. Valid linestyles are (.*?)(?:\.|$)",
        r"linestyle '.*?' is not a valid on-off ink sequence\. Valid linestyles are (.*?)(?:\.|$)",
        r"is not a valid marker\. Valid markers are (.*?)(?:\.|$)",
        r"is not a valid value for backend; supported values are \[(.*?)(?:\.|$)\]",
        r"supported values are \[(.*?)(?:\.|$)\]",
        r"is not a valid value for .*?; supported values are \[(.*?)(?:\.|$)\]",
        r"is not a valid .*?\. Valid .*? are (.*?)(?:\.|$)",
        r"Valid .*? are (.*?)(?:\.|$)",
        r"valid .*? are (.*?)(?:\.|$)",
        r"Supported Postscript/PDF font types are \[(.*?)(?:\.|$)\]",
        r"Supported .*? types are \[(.*?)(?:\.|$)\]",
        r"should be 'tight' or 'standard'",
        r"cannot be interpreted as (.*?)(?:\.|$)",
        r"Not a valid .*? value \[(.*?)(?:\.|$)\]",
        r"Expected a \((.*?)\) triplet",
        r"should be a string that can be parsed by (.*?)(?:\.|$)",
        r"not a valid .*? specification",
        r"bbox should be '(.*?)' or '(.*?)'"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_msg, re.IGNORECASE)
        if match:
            try:
                values_str = match.group(1)
            except:
                #print(f"Could not extract values from error message: {error_msg}") this can occur when no pattern matching happens
                continue
            # Parse the values (handle quotes, commas, etc.)
            values = []
            
            # Handle different formats: quoted strings, unquoted strings, numbers
            # First try to extract quoted strings
            quoted_values = re.findall(r"'([^']*)'|\"([^\"]*)\"", values_str)
            for val in quoted_values:
                val = next(v for v in val if v)  # Get the non-empty value
                if val:
                    values.append(val)
            
            # If no quoted values found, try to extract unquoted values
            if not values:
                # Split by comma and clean up
                parts = values_str.split(',')
                for part in parts:
                    part = part.strip()
                    if part:
                        # Remove brackets if present
                        part = part.strip('[]')
                        if part:
                            values.append(part)
            
            if values:
                return values
    
    # Special handling for specific error patterns
    if "should be 'tight' or 'standard'" in error_msg:
        return ["tight", "standard"]
    elif "cannot be interpreted as True, False, or" in error_msg:
        # Extract the additional option after "or"
        try:
            match = re.search(r"or \"([^\"]+)\"", error_msg)
            if match:
                return ["True", "False", match.group(1)]
            else:
                return ["True", "False"]
        except:
            return ["True", "False"]  # should be a better way to do this
    elif "Expected a (scale, length, randomness) triplet" in error_msg:
        return ["(scale, length, randomness)"]  # This is a special case for tuples
    elif "should be a string that can be parsed by numpy.datetime64" in error_msg:
        return ["1970-01-01", "2000-01-01", "2020-01-01"]  # Example date strings
    
    # Special handling for boolean conversion errors
    if "Could not convert" in error_msg and "to bool" in error_msg:
        return ["True", "False"]
    
    return None

def get_important_parameters():
    """Get list of important plotting-related parameters"""
    important_groups = [
        'axes', 'lines', 'figure', 'font', 'text', 'legend', 'xtick', 'ytick', 
        'grid', 'image', 'savefig'
    ]
    important_params = []
    for param in mpl.rcParams:
        if any(param[:len(group)] == group for group in important_groups):
            important_params.append(param)
    return important_params

def get_changed_parameters():
    """Get list of parameters that differ from defaults"""
    changed_params = []
    for param in mpl.rcParams:
        if mpl.rcParams[param] != default_rcparams[param]:
            changed_params.append(param)
    return changed_params

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, cycler.Cycler): # afaik this is the only one being used
            return str(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)

class ListEditorWidget(QWidget):
    """Custom widget for editing lists and tuples"""
    def __init__(self, value, parent=None):
        super().__init__(parent)
        self.original_value = value
        self.is_tuple = isinstance(value, tuple)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.list_widget.setFixedHeight(100) # Can increase/decrease TODO LOCALVARS?
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(6)
        sizePolicy.setHeightForWidth(self.list_widget.sizePolicy().hasHeightForWidth())
        self.list_widget.setSizePolicy(sizePolicy)
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+")
        self.remove_btn = QPushButton("-")
        self.add_btn.clicked.connect(self.add_item)
        self.remove_btn.clicked.connect(self.remove_item)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        layout.setContentsMargins(0, 0, 0, 0)
        #layout.setSizeConstraint(QLayout.SetFixedSize)
        
        # Populate with current values
        self._populate_list()
        
    def _populate_list(self):
        self.list_widget.clear()
        if isinstance(self.original_value, (list, tuple)):
            for item in self.original_value:
                self.list_widget.addItem(str(item))
        else:
            # Handle single values
            self.list_widget.addItem(str(self.original_value))
            
    def add_item(self):
        item = QListWidgetItem("New Item")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        self.list_widget.editItem(item)
        
    def remove_item(self):
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            self.list_widget.takeItem(current_row)
            
    def get_value(self):
        """Get the current value as a list or tuple"""
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            items.append(item.text())
        
        # Try to convert to appropriate types
        converted_items = []
        for item in items:
            try:
                # Try to convert to number first
                if '.' in item:
                    converted_items.append(float(item))
                else:
                    converted_items.append(int(item))
            except ValueError:
                # Keep as string
                converted_items.append(item)
        
        return tuple(converted_items) if self.is_tuple else converted_items
    
    def set_value(self, value):
        self.original_value = value
        self._populate_list()

class MultiStyleDialog(QDialog):
    """A dialog to select and order multiple Matplotlib styles."""
    styles_selected = pyqtSignal(str)

    def __init__(self, available_styles, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compose Matplotlib Styles")
        self.setMinimumSize(600, 400)

        self.main_layout = QHBoxLayout(self)

        # --- Available Styles ---
        available_group = QGroupBox("Available Styles")
        available_layout = QVBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter styles...")
        self.available_list = QListWidget()
        self.available_list.addItems(sorted(available_styles))
        self.available_list.setSelectionMode(QListWidget.ExtendedSelection)
        available_layout.addWidget(self.filter_edit)
        available_layout.addWidget(self.available_list)
        available_group.setLayout(available_layout)

        # --- Control Buttons (Add/Remove) ---
        controls_layout = QVBoxLayout()
        controls_layout.addStretch()
        add_btn = QPushButton("->")
        add_btn.setToolTip("Add selected style(s)")
        remove_btn = QPushButton("<-")
        remove_btn.setToolTip("Remove selected style(s)")
        controls_layout.addWidget(add_btn)
        controls_layout.addWidget(remove_btn)
        controls_layout.addStretch()

        # --- Selected Styles ---
        selected_group = QGroupBox("Selected Styles (Applied in Order)")
        selected_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        selected_layout.addWidget(self.selected_list)

        # Reorder buttons
        reorder_layout = QHBoxLayout()
        up_btn = QPushButton("Up")
        down_btn = QPushButton("Down")
        reorder_layout.addStretch()
        reorder_layout.addWidget(up_btn)
        reorder_layout.addWidget(down_btn)
        selected_layout.addLayout(reorder_layout)
        selected_group.setLayout(selected_layout)

        # --- OK/Cancel ---
        ok_cancel_layout = QVBoxLayout()
        ok_cancel_layout.addStretch()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_cancel_layout.addWidget(ok_btn)
        ok_cancel_layout.addWidget(cancel_btn)

        # Add all parts to main layout
        self.main_layout.addWidget(available_group, 2)
        self.main_layout.addLayout(controls_layout, 0)
        self.main_layout.addWidget(selected_group, 2)
        self.main_layout.addLayout(ok_cancel_layout, 0)

        # --- Connect Signals ---
        self.filter_edit.textChanged.connect(self._filter_available_styles)
        self.available_list.itemDoubleClicked.connect(self._add_style)
        add_btn.clicked.connect(self._add_styles)
        remove_btn.clicked.connect(self._remove_styles)
        up_btn.clicked.connect(self._move_up)
        down_btn.clicked.connect(self._move_down)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def _filter_available_styles(self, text):
        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _add_styles(self):
        for item in self.available_list.selectedItems():
            self._add_style(item)

    def _add_style(self, item):
        # Avoid adding duplicates
        if not self.selected_list.findItems(item.text(), Qt.MatchExactly):
            self.selected_list.addItem(item.text())

    def _remove_styles(self):
        for item in self.selected_list.selectedItems():
            self.selected_list.takeItem(self.selected_list.row(item))

    def _move_up(self):
        current_row = self.selected_list.currentRow()
        if current_row > 0:
            item = self.selected_list.takeItem(current_row)
            self.selected_list.insertItem(current_row - 1, item)
            self.selected_list.setCurrentRow(current_row - 1)

    def _move_down(self):
        current_row = self.selected_list.currentRow()
        if 0 <= current_row < self.selected_list.count() - 1:
            item = self.selected_list.takeItem(current_row)
            self.selected_list.insertItem(current_row + 1, item)
            self.selected_list.setCurrentRow(current_row + 1)

    def accept(self):
        selected_styles = [self.selected_list.item(i).text() for i in range(self.selected_list.count())]
        if selected_styles:
            composed_name = ", ".join(selected_styles)
            self.styles_selected.emit(composed_name)
        super().accept()

class ParameterTreeWidget(QTreeWidget):
    """Custom tree widget for displaying parameters"""
    parameterChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Parameter", "Value"])
        self.setColumnWidth(0, 250)
        self.param_widgets = {}
        self.changed_params = {}
        self.invalid_params = [] # Only hosts the keys of invalid parameters
        self.known_validators = {}
        self.current_rcparams = mpl.rcParams.copy()

        self.brush_invalid = QBrush(QColor(255, 200, 200))
        self.brush_changed = QBrush(QColor(255, 255, 224))
        self.brush_default = QBrush(QColor(173, 216, 230))
        self.brush_normal = QBrush(Qt.NoBrush)

    def set_known_validators(self, validators):
        """Set the known validators from the parent widget"""
        self.known_validators = validators

    def populate_tree(self, parameter_filter=None):
        """Populate the tree with parameters, optionally filtered"""
        self.clear()
        self.param_widgets.clear()
        
        # Get parameters to display
        if parameter_filter is None:
            # All parameters
            params_to_show = list(mpl.rcParams.keys())
        elif callable(parameter_filter):
            # Filter function
            params_to_show = [p for p in mpl.rcParams.keys() if parameter_filter(p)]
        else:
            # List of specific parameters
            params_to_show = parameter_filter
        
        # Group parameters
        groups = {}
        for key in params_to_show:
            parts = key.split('.')
            group = parts[0] if len(parts) > 1 else 'Other'
            if group not in groups:
                groups[group] = []
            groups[group].append(key)

        for group, keys in sorted(groups.items()):
            group_item = QTreeWidgetItem([group])
            self.addTopLevelItem(group_item)
            
            nested_structure = {}
            for key in keys:
                parts = key.split('.')
                path = parts[1:] if len(parts) > 1 else [key]
                d = nested_structure
                for p in path[:-1]:
                    d = d.setdefault(p, {})
                if '_leaves' not in d:
                    d['_leaves'] = []
                d['_leaves'].append((path[-1], key))

            self._add_nested_items(group_item, nested_structure)
        self.expandAll()

    def _add_nested_items(self, parent, d):
        if '_leaves' in d:
            for leaf_name, full_key in sorted(d['_leaves']):
                self._create_param_item(parent, leaf_name, full_key)
        
        for key, sub_dict in sorted(d.items()):
            if key == '_leaves':
                continue
            node = QTreeWidgetItem([key])
            parent.addChild(node)
            self._add_nested_items(node, sub_dict)

    def _discover_validator(self, key, value):
        """Try to discover the validator for a parameter by testing values"""
        if key in self.known_validators:
            return self.known_validators[key]
        return None

    def _create_param_item(self, parent, name, key):
        value = self.changed_params.get(key, self.current_rcparams[key])
        item = QTreeWidgetItem([name])
        item.setData(0, Qt.UserRole, key)
        parent.addChild(item)

        # Color parameters that differ from defaults
        if value != default_rcparams[key]:
            brush = QBrush(QColor(173, 216, 230))  # Light blue for default-different
            item.setBackground(0, brush)
            item.setBackground(1, brush)

        validator = mpl.RcParams.validate.get(key)
        widget = None

        # Handle different types
        if isinstance(value, bool) or validator is validate_bool:
            widget = QCheckBox()
            widget.setChecked(bool(value))
            widget.toggled.connect(
                lambda checked, k=key, i=item: self._on_value_changed(str(checked), k, i)
            )
        elif isinstance(value, (list, tuple)):
            widget = ListEditorWidget(value)
            # Connect to the list widget's itemChanged signal
            widget.list_widget.itemChanged.connect(
                lambda changedItem, k=key, i=item: self._on_list_value_changed(k, i)
            )
        elif validator and hasattr(validator, 'valid'): # Handles ValidateInStrings and similar classes
            widget = QComboBox()
            widget.addItems(validator.valid)
            if str(value) in validator.valid:
                widget.setCurrentText(str(value))
            else:
                widget.addItem(str(value))
                widget.setCurrentText(str(value))
            widget.setEditable(True)  # Make all dropdowns editable
            widget.currentTextChanged.connect(
                lambda text, k=key, i=item: self._on_value_changed(text, k, i)
            )
        else:
            # Try to discover validator
            discovered_values = self._discover_validator(key, value)
            if discovered_values:
                widget = QComboBox()
                widget.addItems([str(v) for v in discovered_values])
                if str(value) in [str(v) for v in discovered_values]:
                    widget.setCurrentText(str(value))
                else:
                    widget.addItem(str(value))
                    widget.setCurrentText(str(value))
                widget.setEditable(True)  # Make all dropdowns editable
                widget.currentTextChanged.connect(
                    lambda text, k=key, i=item: self._on_value_changed(text, k, i)
                )
            else:
                widget = QLineEdit(str(value))
                widget.textChanged.connect(
                    lambda text, k=key, i=item: self._on_value_changed(text, k, i)
                )
        
        if widget:
            self.setItemWidget(item, 1, widget)
            self.param_widgets[key] = widget

    def _on_value_changed(self, new_value_str, key, item):
        original_value = self.current_rcparams[key]
        is_bool = isinstance(original_value, bool)
        original_value_str = str(original_value)
        
        # Handle boolean string comparison
        if is_bool:
            current_as_bool_str = "True" if original_value else "False"
            is_different = current_as_bool_str != new_value_str
        else:
            is_different = new_value_str != original_value_str

        if is_different:
            brush = self.brush_changed if key not in self.invalid_params else self.brush_invalid  # Light yellow for changed
            item.setBackground(0, brush)
            item.setBackground(1, brush)
            self.changed_params[key] = new_value_str
        else:
            # Check if it differs from default... No need to check if it's invalid, cause it would be changed otherwise
            # Nevermind on the invalid, lets continue assuming its not valid until the user hits apply again
            if original_value != default_rcparams[key]:
                brush = self.brush_default  # Light blue for default-different
                item.setBackground(0, brush)
                item.setBackground(1, brush)
            else:
                item.setBackground(0, self.brush_normal)
                item.setBackground(1, self.brush_normal)
            if key in self.changed_params:
                del self.changed_params[key]

        self.parameterChanged.emit()

    def _on_list_value_changed(self, key, item):
        """Handle changes in list/tuple editors"""
        widget = self.itemWidget(item, 1)
        if isinstance(widget, ListEditorWidget):
            new_value = widget.get_value()
            original_value = self.current_rcparams[key]
            
            is_different = new_value != original_value
            
            if is_different:
                brush = self.brush_changed if key not in self.invalid_params else self.brush_invalid  # Light yellow for changed
                item.setBackground(0, brush)
                item.setBackground(1, brush)
                self.changed_params[key] = new_value
            else:
                # Check if it differs from default
                if original_value != default_rcparams[key]:
                    brush = self.brush_default  # Light blue for default-different
                    item.setBackground(0, brush)
                    item.setBackground(1, brush)
                else:
                    item.setBackground(0, self.brush_normal)
                    item.setBackground(1, self.brush_normal)
                if key in self.changed_params:
                    del self.changed_params[key]

        self.parameterChanged.emit()

    def get_changed_params(self):
        """Get all changed parameters from all trees"""
        return self.changed_params.copy()

    def refresh(self, clear=True):
        """Refresh the tree with current rcParams"""
        self.current_rcparams = mpl.rcParams.copy()
        if clear: self.changed_params.clear()
        # Re-populate with current filter
        # This will be handled by the parent widget

    def mark_invalid_param(self, key, invalid_value):
        """Mark a parameter as invalid with red coloring"""
        # Find the item and color it red
        self.invalid_params.append(key)
        for i in range(self.topLevelItemCount()):
            if self._mark_invalid_in_tree(self.topLevelItem(i), key, invalid_value):
                break

    def _mark_invalid_in_tree(self, item, key, invalid_value):
        """Recursively search and mark invalid parameters in the tree"""
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() == 0:
                # This is a parameter item
                item_key = child.data(0, Qt.UserRole)
                if item_key == key:
                    # Color the item red
                    brush = self.brush_invalid  # Light red for invalid
                    child.setBackground(0, brush)
                    child.setBackground(1, brush)
                    # Update the widget with the invalid value
                    widget = self.itemWidget(child, 1)
                    if widget:
                        if isinstance(widget, QLineEdit):
                            widget.setText(str(invalid_value))
                        elif isinstance(widget, QComboBox):
                            if str(invalid_value) not in [widget.itemText(j) for j in range(widget.count())]:
                                widget.addItem(str(invalid_value))
                            widget.setCurrentText(str(invalid_value))
                        elif isinstance(widget, QCheckBox):
                            widget.setChecked(bool(invalid_value))
                        elif isinstance(widget, ListEditorWidget):
                            widget.set_value(invalid_value)
                    return True
            else:
                if self._mark_invalid_in_tree(child, key, invalid_value):
                    return True
        return False

    def clear_invalid_markings(self):
        """Clear all red coloring and restore normal coloring"""
        self.invalid_params.clear()
        for i in range(self.topLevelItemCount()):
            self._reset_coloring_in_tree(self.topLevelItem(i))

    def _reset_coloring_in_tree(self, item):
        """Recursively reset coloring in the tree"""
        for i in range(item.childCount()):
            child = item.child(i)
            if child.childCount() == 0:
                # This is a parameter item
                key = child.data(0, Qt.UserRole)
                if key:
                    # Reset to appropriate coloring based on current state
                    current_value = self.current_rcparams[key]
                    if key in self.invalid_params:
                        brush = self.brush_invalid  # Light red for invalid
                    elif key in self.changed_params:
                        brush = self.brush_changed  # Light yellow for changed
                    elif current_value != default_rcparams[key]:
                        brush = self.brush_default  # Light blue for default-different
                    else:
                        brush = self.brush_normal
                    child.setBackground(0, brush)
                    child.setBackground(1, brush)
            else:
                self._reset_coloring_in_tree(child)

class MplRcParamsWidget(QWidget):
    """Widget for editing matplotlib rcParams"""
    applyPressed = pyqtSignal()  # Signal emitted when apply is pressed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_rcparams = mpl.rcParams.copy()
        self.changed_params = {}
        self.known_validators = discover_rcparam_validators()  # Use discovered validators
        self._init_ui()
        self.refresh_all()

    def _init_ui(self):
        layout = QVBoxLayout()
        # this is too much in a dock: layout.setContentsMargins(0,0,0,0)

        style_layout = QHBoxLayout()
        style_label = QLabel("Matplotlib Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(['default', 'custom'] + plt.style.available)
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        self.style_compose_btn = QPushButton("Compose...")
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        style_layout.addWidget(self.style_compose_btn)
        layout.addLayout(style_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create three tree widgets for different views
        self.all_tree = ParameterTreeWidget()
        self.important_tree = ParameterTreeWidget()
        self.changed_tree = ParameterTreeWidget()
        
        # Pass the known validators to each tree
        self.all_tree.set_known_validators(self.known_validators)
        self.important_tree.set_known_validators(self.known_validators)
        self.changed_tree.set_known_validators(self.known_validators)
        
        # Populate trees
        self.all_tree.populate_tree()  # All parameters
        self.important_tree.populate_tree(get_important_parameters())  # Important parameters
        self.changed_tree.populate_tree(get_changed_parameters())  # Changed parameters
        
        # Add tabs
        self.tab_widget.addTab(self.changed_tree, "Changed Parameters")
        self.tab_widget.addTab(self.important_tree, "Common Parameters")
        self.tab_widget.addTab(self.all_tree, "All Parameters")
        
        layout.addWidget(self.tab_widget)

        # Button layout
        btn_layout = QHBoxLayout()

        self.import_btn = QPushButton("Import")
        self.export_btn = QPushButton("Export")
        self.refresh_btn = QPushButton("Refresh")
        self.apply_btn = QPushButton("Apply")
        self.reset_btn = QPushButton("Reset to Default")
        self.cancel_btn = QPushButton("Cancel")

        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Connect signals
        self.import_btn.clicked.connect(self._import_rcparams)
        self.export_btn.clicked.connect(self._export_rcparams)
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.apply_btn.clicked.connect(self.apply_changes)
        self.reset_btn.clicked.connect(self.reset_defaults)
        self.cancel_btn.clicked.connect(self.clear_changes)
        self.style_compose_btn.clicked.connect(self._show_style_compose_dialog)

        # Connect changes
        self.all_tree.parameterChanged.connect(self._on_param_change)
        self.important_tree.parameterChanged.connect(self._on_param_change)
        self.changed_tree.parameterChanged.connect(self._on_param_change)

        # Create compose dialog instance just to have ready
        self.style_compose_dialog = MultiStyleDialog(plt.style.available, self)
        self.style_compose_dialog.styles_selected.connect(self._on_style_changed)


    def _change_style_combo_text(self, new_text):
        self.style_combo.blockSignals(True)
        self.style_combo.setCurrentText(new_text)
        self.style_combo.blockSignals(False)

    def _on_param_change(self):
        """Sets the style combo to 'custom' when a parameter is changed manually."""
        if self.style_combo.currentText() != 'custom':
            self._change_style_combo_text('custom')

    def _on_style_changed(self, style_name, silent = False):
        if not style_name or style_name == 'custom':
            return
        #self.style_combo.blockSignals(True)
        try:
            logger.info(f"Applying matplotlib style: {style_name}")
            if ',' in style_name: # It is a composition!
                if self.style_combo.findText(style_name) == -1: # Add it just incase its a *new* composition
                    self.style_combo.addItem(style_name)
                plt.style.use([s.strip() for s in style_name.split(',')]) # Can justhave this
            else: # can remove this and deindent the line prior
                plt.style.use(style_name) # This can honestly probably be removed, if no ',' is present, it would supply a list of len==1 which should still be okay!
            self.refresh_all()
        except Exception as e:
            if not silent: QMessageBox.warning(self, "Style Error", f"Could not apply style '{style_name}':\n{e}")
            logger.error(f"Could not apply style '{style_name}': {e}")
        finally:
            # self.style_combo.setCurrentText('custom')
            self._change_style_combo_text(style_name) # Just in case
            # self.style_combo.blockSignals(False)

    def refresh_all(self, clear = True):
        """Refresh all trees with current rcParams state"""
        self.current_rcparams = mpl.rcParams.copy()
        
        # Refresh each tree
        self.all_tree.refresh(clear = clear)
        self.all_tree.populate_tree()
        
        self.important_tree.refresh(clear = clear)
        self.important_tree.populate_tree(get_important_parameters())
        
        self.changed_tree.refresh(clear = clear)
        self.changed_tree.populate_tree(get_changed_parameters())

    def apply_changes(self):
        # Collect changes from all trees
        all_changes = {}
        all_changes.update(self.all_tree.get_changed_params())
        all_changes.update(self.important_tree.get_changed_params())
        all_changes.update(self.changed_tree.get_changed_params())
        
        unchanged_keys = []
        invalid_keys = []  # Track keys that had validation errors
        
        for key, value_str in all_changes.items():
            try:
                # Let matplotlib handle the conversion from string
                mpl.rcParams[key] = value_str
                #changed_keys.append(key)
            except Exception as e:
                error_msg = str(e)
                
                # Try to extract allowed values from error message
                allowed_values = extract_allowed_values_from_error(error_msg)

                # Show dialog with discovered values
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("Invalid Value")
                if allowed_values:
                    # Cache the discovered validator
                    self.known_validators[key] = allowed_values
                    msg_box.setText(f"Invalid value for '{key}': '{value_str}'\n\nAllowed values: {', '.join(allowed_values)}\n\nWould you like to revert this change?")
                else:
                    msg_box.setText(f"Could not set '{key}' to '{value_str}':\n\n{e}")
                
                msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                msg_box.button(QMessageBox.Ok).setText("Go back and change value")
                msg_box.button(QMessageBox.Cancel).setText("Revert to valid value")
                
                reply = msg_box.exec_()
                
                if reply == QMessageBox.Ok:  # User clicked "Go back and change value"
                    unchanged_keys.append(key)
        
        self.current_rcparams = mpl.rcParams.copy()

        # Clear changes from all trees (except invalid ones)
        self.all_tree.changed_params = {key: value for key, value in self.all_tree.changed_params.items() if key in unchanged_keys}
        self.important_tree.changed_params = {key: value for key, value in self.important_tree.changed_params.items() if key in unchanged_keys}
        self.changed_tree.changed_params = {key: value for key, value in self.changed_tree.changed_params.items() if key in unchanged_keys}

        # Refresh all trees to show current state (but preserve invalid values)
        self.refresh_all(clear = False) # Note: this resets changed_params{} dict, so we reapply


        # Clear invalid markings after refresh
        self.all_tree.clear_invalid_markings()
        self.important_tree.clear_invalid_markings()
        self.changed_tree.clear_invalid_markings()
        
        # Re-mark invalid parameters after refresh
        for key in unchanged_keys:
            invalid_value = all_changes.get(key)
            if invalid_value is not None:
                self.all_tree.mark_invalid_param(key, invalid_value)
                self.important_tree.mark_invalid_param(key, invalid_value)
                self.changed_tree.mark_invalid_param(key, invalid_value)
        
        # Emit signal when apply is successful
        if len(unchanged_keys) == 0:
            self.applyPressed.emit()

    def clear_changes(self):
        """Clear all changes and reset to original values"""
        self.all_tree.changed_params.clear()
        self.important_tree.changed_params.clear()
        self.changed_tree.changed_params.clear()
        self.refresh_all()

    def reset_defaults(self):
        reply = QMessageBox.question(self, 'Reset rcParams', 
                                   "Are you sure you want to reset all Matplotlib parameters to their default values?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            mpl.rcdefaults()
            self.refresh_all()
            self._change_style_combo_text('default')

    def _import_rcparams(self, file_path = None, silent = False):
        """Loads rcParams from a JSON file and applies them"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Import Matplotlib Style", "mpl_style.json", "JSON Style Files (*.json)")
            if not file_path:
                return
        try:
            with open(file_path, 'r') as f:
                styles = json.load(f)

                # maybe we want something less harsh
                if MPL_USE_STYLE_BACKEND:
                    plt.style.use({k:v for k,v in styles['params'].items() if k not in STYLE_BLACKLIST}) # It can take {k:v} of rcparam pairs, automatically ignores stuff that can crash it
                else:
                    rcparams = default_rcparams.copy()
                    rcparams.update(styles['params'])
                    mpl.rcParams.update(rcparams)
                if styles['style'] and styles['style'] != 'custom':
                    self._on_style_changed(styles['style'], silent=True)  # Silently update the style
                self.refresh_all()
                logger.info(f"Imported style from '{file_path}")
                if not silent: self.applyPressed.emit()

        except Exception as e:
            if not silent: QMessageBox.warning(self, "Import Error", f"Failed to import rcParams from '{file_path}':\n{e}")
            logger.error(f"Failed to import rcParams from '{file_path}': {e}")

    def _export_rcparams(self, file_path = None, silent = False):
        """Saves current rcParams changes to a JSON file"""
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Matplotlib Style", "mpl_style.json", "JSON Style Files (*.json)")
            if not file_path:
                return
        try:
            current_params = {k: v for k, v in mpl.rcParams.items() if default_rcparams[k] != v}
            # Uncomment this is to debug the Numpy encoder, which doesnt appear to really be putting in work
            # current_params = mpl.rcParams.copy()
            if MPL_USE_STYLE_BACKEND: # can make it fancy with dict(filter(etc))
                current_params = {k:v for k,v in current_params.items() if k not in STYLE_BLACKLIST} # Prevent it from bugging


            # Lets determine if there are any unsaved changes
            all_changes = {}
            all_changes.update(self.all_tree.get_changed_params())
            all_changes.update(self.important_tree.get_changed_params())
            all_changes.update(self.changed_tree.get_changed_params())

            if len(all_changes) and not silent:
                # Unsaved changes
                #msg_box = QMessageBox.question(self, "You have unapplied changes.", "Would you like to apply these changes before exporting?", QMessageBox.Yes | QMessageBox.No)
                #if msg_box == QMessageBox.Yes:
                #    # Try applying these changes first
                #    self.apply_changes()
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Question)
                msg_box.setWindowTitle("Unsaved Changes")
                msg_box.setText("You have unapplied changes.")
                msg_box.setInformativeText("Do you want to apply these changes before exporting?")

                apply = msg_box.addButton("Apply and Export", QMessageBox.AcceptRole)
                ignore = msg_box.addButton("Export Current (Ignore Changes)", QMessageBox.ActionRole)
                _ = msg_box.addButton("Cancel", QMessageBox.RejectRole)

                msg_box.exec_()
                clicked_button = msg_box.clickedButton()

                if clicked_button == apply: # Apply changes first
                    self.apply_changes()
                elif clicked_button == ignore:
                    pass
                else: # Cancelled or error
                    return

            with open(file_path, 'w') as f:
                json.dump({
                    'style': self.style_combo.currentText(),
                    'params':current_params
                }, f, indent=4, cls=NumpyEncoder)
            if not silent: QMessageBox.information(self, "Export Successful", f"Style saved to:\n'{file_path}'")
            logger.info(f"Style saved to '{file_path}'")
        except Exception as e:
            if not silent: QMessageBox.information(self, "Export Error", f"Failed to export style to '{file_path}':\n{e}")
            logger.error(f"Failed to export rcParams to '{file_path}': {e}")

    ### Style Composer

    def _show_style_compose_dialog(self):
        self.style_compose_dialog.exec_() # Is it .show() instead??




def create_test_plot():
    """Create a test plot to demonstrate the rcParams changes"""
    plt.figure(figsize=(10, 6))
    
    # Create some sample data
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x)
    y2 = np.cos(x)
    y3 = np.tan(x)
    
    # Plot with different styles
    plt.plot(x, y1, label='sin(x)', linewidth=2, linestyle='-', marker='o', markersize=4)
    plt.plot(x, y2, label='cos(x)', linewidth=2, linestyle='--', marker='s', markersize=4)
    plt.plot(x, y3, label='tan(x)', linewidth=2, linestyle='-.', marker='^', markersize=4)
    
    plt.xlabel('X Axis')
    plt.ylabel('Y Axis')
    plt.title('Test Plot - rcParams Demonstration')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create the widget
    widget = MplRcParamsWidget()
    
    # Connect the signal to create a test plot
    widget.applyPressed.connect(create_test_plot)
    
    # Create a simple dialog to contain the widget
    dialog = QDialog()
    dialog.setWindowTitle("Matplotlib rcParams Editor")
    dialog.resize(800, 600)
    
    layout = QVBoxLayout()
    layout.addWidget(widget)
    dialog.setLayout(layout)
    
    # Show the dialog
    dialog.show()
    
    sys.exit(app.exec_())