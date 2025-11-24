import os
import sys
import importlib.util
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QListWidget, QPushButton,
    QInputDialog, QMessageBox, QAbstractItemView, QDialogButtonBox, QLabel, QComboBox,
    QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt
from logger import get_logger

from gui.plot_module_widget import ModuleConfigDialog
from gui.parameter_form_widget import ParameterFormWidget

"""
Notes:

Should we add target columns to pipeline instead of inside the pipeline parameters?

Currently, a module can override 'target_column' parameter and mess everything up

"""

# Define the directory for manipulation modules.
# TODO: Move this to localvars.py.

MANIPULATION_MODULES_DIR = 'manipulation_modules' # Note that this is always run from root directory
if not os.path.exists(MANIPULATION_MODULES_DIR):
    os.makedirs(MANIPULATION_MODULES_DIR)

logger = get_logger(__name__)



# Base Manipulation Module (TODO: MOVE ALL BASE CLASSES TO COMMON FILE IN ROOT, LIKE processing_base.py (maybe call it core?)

class ManipulationModule:
    """Base class for all data manipulation modules."""
    name = "Base Manipulator"
    description = "A base class for data manipulation."
    # PARAMETERS can be defined here for modules that need configuration.
    # e.g., PARAMETERS = [('param_name', 'Param Label', str, True, 'default_value')]
    # TODO: Comment this out and do same global/override PARAMETERS config as plot_modules (for multiple types of manipulations for example)
    PARAMETERS = []

    def __init__(self, params=None):
        self.params = params or {}

    def target_columns(self):
        return self.params.get('target_columns', [])

    def process(self, df):
        """
        Process the DataFrame and return the modified DataFrame.
        This method must be overridden by subclasses.
        :param df: The pandas DataFrame to process.

        TODO: Do we need to return df since we modify it inline? Should we force a copy?
        """
        raise NotImplementedError("Each manipulation module must implement the process method.")


# Module discovery (maybe unify with DataManagement.module_loader)
def discover_manipulation_modules(modules_dir=MANIPULATION_MODULES_DIR):
    """
    Discovers manipulation modules from the specified directory.
    Returns a list of (module_name, module_class) tuples.

    TODO: Load parameters here for global
    """
    modules = []
    if not os.path.exists(modules_dir):
        logger.warning(f"Manipulation modules directory not found: {modules_dir}")
        return modules

    for filename in os.listdir(modules_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = filename[:-3]
            module_path = os.path.join(modules_dir, filename)
            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, ManipulationModule) and attr != ManipulationModule:
                        # Use the class's `name` attribute for display
                        params = getattr(attr, 'PARAMETERS', getattr(module, 'PARAMETERS', []))
                        modules.append((attr.name, attr, params))
            except Exception as e:
                logger.error(f"Error loading manipulation module {filename}: {e}")
    return modules


# Apply pipeline (Should be called when plotting)
def apply_manipulation_pipeline(df, pipeline):
    """
    Applies a series of manipulation modules to a DataFrame.
    :param df: The input pandas DataFrame.
    :param pipeline: A list of manipulation steps (List[dict]).
    :return: The processed pandas DataFrame (COPY)
    """
    if not pipeline:
        return df

    logger.info(f"Applying manipulation pipeline: {[step['name'] for step in pipeline]}")
    current_df = df.copy()

    try:
        available_modules = {name:cls for name,cls,_ in discover_manipulation_modules()}
    except Exception as e:
        logger.error(f"Could not discover manipulation modules: {e}")
        raise RuntimeError(f"Could not load manipulation modules: {e}")

    for i, step in enumerate(pipeline):
        module_name = step['name']
        module_params = step.get('params', {})
        if module_name in available_modules:
            module_class = available_modules[module_name]
            try:
                instance = module_class(params=module_params)
                current_df = instance.process(current_df)
                if current_df is None:
                    raise ValueError(f"Module '{module_name}' process() method returned None.")
            except Exception as e:
                logger.error(f"Error applying manipulator '{module_name}': {e}")
                # Re-raise with more context
                raise RuntimeError(f"Error during '{module_name}' step: {e}") from e
        else:
            raise RuntimeError(f"Manipulation module '{module_name}' not found.")

    return current_df


# Interfacing widgets

class ManipulationDialog(QDialog):
    """A dialog for managing the entire manipulation pipeline."""
    def __init__(self, pipeline, data_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Manipulation Pipeline") # Change?
        self.setMinimumSize(500, 500)

        layout = QVBoxLayout(self)
        self.pipeline_widget = ManipulationPipelineWidget(self, data_columns=data_columns)
        self.pipeline_widget.set_pipeline(pipeline)
        layout.addWidget(self.pipeline_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_pipeline(self):
        return self.pipeline_widget.get_pipeline()

class ManipulationConfigDialog(QDialog):
    universal_params = [
        ('target_columns_%d', 'Columns to Manipulate', 'dropdown_column', True, None)
    ]
    def __init__(self, modules, current_module = None, current_parameters = None, data_columns = None,parent = None):
        super().__init__(parent)
        self.setWindowTitle('Configure Manipulation')
        self.modules = modules
        self.data_columns = data_columns

        self.parameter_form_widget = None
        self.parameter_container = None
        self.parameter_container_layout = None

        self.module_combo = None

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)

        self._init_ui(current_module = current_module, current_parameters = current_parameters)

    def _init_ui(self, current_module = None, current_parameters = None):
        layout = QVBoxLayout(self)

        # Lets make the module selection span horizontally. I'm sure theres a better way to do this but I do not know it
        module_widget, module_layout = QWidget(), QHBoxLayout()
        module_widget.setLayout(module_layout)
        module_layout.setContentsMargins(0,0,0,0)

        # Module code
        module_label = QLabel("Module:")
        self.module_combo = QComboBox()
        self.module_combo.setObjectName('module_combo')
        self.module_combo.addItems([name for name,*_ in self.modules])

        # The combo box size is a good way to set the minimum dialog size
        self.module_combo.setMinimumWidth(200)
        self.module_combo.setSizePolicy(self.sizePolicy().Expanding, self.sizePolicy().Expanding)

        # Configure module layout
        module_layout.addWidget(module_label)
        module_layout.addWidget(self.module_combo)
        layout.addWidget(module_widget)
        layout.addWidget(self.description_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        self.parameter_container = QWidget()
        self.parameter_container_layout = QVBoxLayout(self.parameter_container)
        self.parameter_container_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.parameter_container)

        # Add buttons
        ok_cancel_reset = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(lambda: self._on_module_changed(self.module_combo.currentIndex()))
        ok_cancel_reset.addWidget(reset_btn)
        ok_cancel_reset.addStretch(1)
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        ok_cancel_reset.addWidget(ok_btn)
        ok_cancel_reset.addWidget(cancel_btn)
        layout.addLayout(ok_cancel_reset)
        layout.setSizeConstraint(layout.SetFixedSize)

        if current_module and current_module in (module_names := [name for name, *_ in self.modules]):
            current_index = module_names.index(current_module)
            self.module_combo.setCurrentIndex(current_index)
            self._on_module_changed(current_index, current_parameters)
        else:
            self._on_module_changed(0)

        self.module_combo.currentIndexChanged.connect(self._on_module_changed)

    def _on_module_changed(self, idx, current_parameters = None):
        # Clear old widgets
        if self.parameter_form_widget:
            self.parameter_container_layout.removeWidget(self.parameter_form_widget)
            self.parameter_form_widget.deleteLater()
            self.parameter_form_widget = None

        if idx < 0 or idx >= len(self.modules):
            return

        name, cls, parameters = self.modules[idx]
        self.description_label.setText(getattr(cls, 'description', ''))
        self.selected_module = cls
        # Create the new form widget
        self.parameter_form_widget = ParameterFormWidget(self.universal_params + parameters, self.data_columns, None)
        if current_parameters: self.parameter_form_widget.set_params(current_parameters)
        self.parameter_container_layout.addWidget(self.parameter_form_widget)

    def get_module(self):
        return self.modules[self.module_combo.currentIndex()]
    def get_params(self):
        return self.parameter_form_widget.get_params()

class ManipulationPipelineWidget(QWidget):
    """
    A widget for creating and managing a pipeline of data manipulation modules.
    """


    def __init__(self, parent=None, data_columns=None):
        super().__init__(parent)
        self.data_columns = data_columns or []
        self._pipeline = []  # List of {'name': str, 'params': dict}
        self._available_modules = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Data Manipulation Pipeline (Applied in Order)")
        layout = QVBoxLayout()

        self.pipeline_list = QListWidget()
        self.pipeline_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.pipeline_list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self.pipeline_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        configure_btn = QPushButton("Configure")
        remove_btn = QPushButton("Remove")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(configure_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        group.setLayout(layout)
        main_layout.addWidget(group)

        add_btn.clicked.connect(self._add_step)
        configure_btn.clicked.connect(self._configure_step)
        remove_btn.clicked.connect(self._remove_step)

        # Also allow configuration on double-click
        self.pipeline_list.itemDoubleClicked.connect(self._configure_step)

    def _load_available_modules(self):
        """Discovers manipulation modules."""
        self._available_modules = (discover_manipulation_modules())
        logger.info(f"Discovered manipulation modules: {[name for name,*_ in self._available_modules]}")

    def _refresh_list_widget(self):
        self.pipeline_list.clear()
        for step in self._pipeline:
            item = QListWidgetItem(step['name'])
            # Store the full config in the item for easy access
            item.setData(Qt.UserRole, step)
            self.pipeline_list.addItem(item)

    def _add_step(self):
        if not self._available_modules:
            self._load_available_modules()
        if not self._available_modules:
            QMessageBox.warning(self, "No Modules Found",
                                "Could not find any manipulation modules in the 'manipulation_modules' directory.")
            return
        # TODO: Make custom QDialog which will have configuration field in it, so it can be configured when added

        dialog = ManipulationConfigDialog(self._available_modules, parent=self, data_columns=self.data_columns)
        if dialog.exec_() == QDialog.Accepted:
            module_name, *_ = dialog.get_module()
            self._pipeline.append({'name': module_name, 'params': dialog.get_params()})
            self._refresh_list_widget()

        #module_name, ok = QInputDialog.getItem(self, "Add Manipulation Step", "Select Module:", self._available_modules.keys(), 0, False)
        #if ok and module_name:
        #    # Add with default parameters
        #    self._pipeline.append({'name': module_name, 'params': {}})
        #    self._refresh_list_widget()

    def _remove_step(self):
        current_row = self.pipeline_list.currentRow()
        if current_row >= 0:
            del self._pipeline[current_row]
            self._refresh_list_widget()

    def _configure_step(self):
        current_item = self.pipeline_list.currentItem()
        if not current_item:
            return

        current_row = self.pipeline_list.row(current_item)
        step_config = self._pipeline[current_row]
        module_name = step_config['name']

        try:
            self._available_modules = discover_manipulation_modules()
            _, module_class, module_specific_params = next((name, cls, params) for name, cls, params in self._available_modules if name == module_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load manipulation modules: {e}")
            return

        if not module_class:
            QMessageBox.warning(self, "Module Not Found", f"The module '{module_name}' could not be found.")
            return

        # Get the module's specific parameters
        #module_specific_params = getattr(module_class, 'PARAMETERS', [])

        # Prepend a universal 'target_columns' parameter to every module's config dialog.
        # This makes it easy for modules to know which columns to operate on.
        universal_params = [
            ('target_columns_%d', 'Columns to Manipulate', 'dropdown_column', True, None)
        ]

        # Combine universal and module-specific parameters for the dialog
        full_parameters = module_specific_params

        """
        # Temporarily stealing until we make our own closer to processing_dialog.py (See TODO above)
        dialog = ModuleConfigDialog(
            module_name,
            full_parameters,
            current_values=step_config.get('params', {}),
            data_columns=self.data_columns,
            parent=self
        )
        """
        dialog = ManipulationConfigDialog(
            self._available_modules,
            data_columns=self.data_columns,
            current_module=module_name,
            current_parameters=step_config.get('params', {}),
            parent=self
        )

        # Update pipline parameters
        if dialog.exec_() == QDialog.Accepted:
            name, cls, parameters = dialog.get_module()
            self._pipeline[current_row]['params'] = dialog.get_params()

            if name != module_name:
                logger.debug(f"Manipulation module changed from {module_name} to {name}.")
                self._pipeline[current_row]['name'] = name
                self._refresh_list_widget()
            logger.info(f"Updated parameters for '{name}': {self._pipeline[current_row]['params']}")

    def _on_rows_moved(self, parent, start, end, dest, dest_row):
        """Updates the internal pipeline list when items are reordered in the UI."""
        # The logic for list reordering is tricky. When an item is moved,
        # its final position depends on whether it was moved up or down.
        # TODO: implement this logic in line_list_widget
        moved_item = self._pipeline.pop(start)
        if dest_row > start:
            # Moved down, the destination index is one less than reported
            # because the item was removed from before it.
            self._pipeline.insert(dest_row - 1, moved_item)
        else:
            # Moved up, the destination index is correct.
            self._pipeline.insert(dest_row, moved_item)

        # No need to call _refresh_list_widget, the UI should already be updated.
        # We just need to ensure our internal list matches. TODO: TEST

    def get_pipeline(self):
        return self._pipeline

    def set_pipeline(self, pipeline):
        if isinstance(pipeline, list):
            self._pipeline = pipeline
            self._refresh_list_widget()