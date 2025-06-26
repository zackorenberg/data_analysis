# Creating Custom Processing Modules

This document explains how to create custom data processing modules that can be discovered and used by the main application.

## Introduction

The processing module system allows you to write custom Python scripts that can be applied to data files directly from the GUI. When you right-click a file and choose "[Pre/Post]process with...", the application scans this directory for valid modules and presents them as options. Each module can define a unique set of parameters, which are used to build a configuration dialog on the fly.

## Core Concepts

1.  **Module Discovery**: The application looks for any `.py` file in this directory. Each file can contain one or more module classes.
2.  **Module Type (`MODE`)**: Each module file must define a top-level `MODE` constant. This determines where the module will appear in the GUI's context menu.
    -   `MODE = 'pre'`: The module will appear under "Preprocess with...".
    -   `MODE = 'post'`: The module will appear under "Postprocess with...".
    -   `MODE = ['pre', 'post']`: The module will appear in both menus.
3.  **Base Class**: Your module class must inherit from `BasePreprocessingModule` or `BasePostprocessingModule` (defined in `processing_base.py`).
4.  **Parameters (`PARAMETERS`)**: Each module file must define a `PARAMETERS` list. This list of tuples or dicts defines the user-configurable parameters that will be shown in the processing dialog.

## Creating a New Module: Step-by-Step

### 1. Create the Python File

Create a new file in this directory, for example, `normalize_data.py`.

### 2. Define `MODE` and `PARAMETERS`

At the top of your file, define the `MODE` and the `PARAMETERS` list. The `PARAMETERS` list is a list of tuples, where each tuple defines one parameter widget.

The format for a parameter tuple is: `(name, label, type, required, placeholder)`

-   `name` (str): The internal variable name for the parameter.
-   `label` (str): The user-friendly text label shown in the dialog.
-   `type` (str or type): The kind of widget to create. Supported types include:
    -   `str`, `int`, `float`: Creates a `QLineEdit`. This can be any instance of `type`.
    -   `'checkbox'` or `bool`: Creates a `QCheckBox`.
    -   `'dropdown'` or `'dropdown_column'`: Creates a `QComboBox` populated with the columns from the input data file.
    -   `('Option 1', 'Option 2')`: A tuple/list of strings creates a `QComboBox` with those specific items.
    -   `'label'`: Creates a non-editable `QLabel`. The `placeholder` will be its text.
-   `required` (bool): If `True`, the user may provide a default value for this parameter below.
-   `placeholder` (any, optional): A default or placeholder value for the widget.

### 3. Create the Module Class

Define a class that inherits from the appropriate base class.

-   `__init__(self, input_file, output_dir, params, data)`: The constructor receives all necessary information. `params` is a dictionary containing the values configured by the user in the dialog. `data` is the pre-loaded DataFrame from the input file.
-   `load(self)`: Handles additional loading logic the user may wish to overload. This method is usually empty (`pass`) as the GUI pre-loads the data for you and supplies it in `__init__()`. You may omit this overload entirely.
-   `process(self)`: This is the core method where you implement your data manipulation logic. You should operate on `self.data` and store the final DataFrame in `self.result`.
-   `save(self)`: This method handles saving `self.result`. You can use the helper `self.save_data(...)` or `self.save_data_numpy(...)` from the base class.

Optionally, a name and description can be supplied in the processing module definition. Furthermore, `PARAMETERS` may be optionally overridden as well. An example is shown below.

---

### 4. Advanced Parameters

You can create more complex, dynamic forms for your parameters.

## Multi-Value Parameters

To allow a user to add multiple text fields for a single parameter (e.g., a list of masks), use the `_%d` suffix in the parameter `name`.

This will be collected into a list in your `params` dictionary, e.g., `params['ignore_column'] = ['col1', 'col2']`.

## Multi-Group Parameters

To create a repeatable group of several related parameters, define the `type` as a dictionary. For example, a multi-valued multi-grouped parameters "Filters"

```py
PARAMETERS = [
    ...
    ('filters_%d', 'Filters', {
        'type': 'multi',
        'fields': [
            ('column', 'Column', 'dropdown_column', True, ''),
            ('threshold', 'Threshold', 'float', True, ''),
        ]
    }, False, None),
    ...
]
```

This will be collected as a list of dictionaries, e.g., `params['filters'] = [{'column': 'Vx', 'threshold': 1.5}, {'column': 'Vy', 'threshold': 2.0}]`.


### Full Example

Here is a complete example of a simple pre-processing module, `offset_column.py`. This module adds a user-defined offsets to selected columns and saves the result as a new file. There are two implementations shown, one which leverages the `multi` typing, and one that overrides `PARAMETERS` for single-column offsetting.

```py
# In processing_modules/offset_column.py

from processing_base import BaseProcessingModule
import pandas as pd

# Step 1. Define the module type
MODE = 'pre'

# Step 2. Define the user-configurable parameters
PARAMETERS = [
    # (name, label, type, required, placeholder)
    ('columns_%d', 'Column(s) to Offset', {
        'type':'multi',
        'fields':[
            ('target_column', 'Column', 'dropdown_column', True),
            ('offset_value', 'Offset Value', float, True, 'e.g., -1.25'),
        ],
    }, True),
    ('output_filename', 'Output Filename', str, True, 'offset_data.dat')
]

# Step 3. Create the module class(es)
class OffsetColumn(BaseProcessingModule):
    name = 'Offset Columns'
    description = 'Offsets multiple columns by specified values'

    """
    Applies a simple numerical offset to a specified column.
    """
    def __init__(self, input_file, output_dir, params, data):
        # It's crucial to call the parent's __init__
        super().__init__(input_file, output_dir, params)
        self.data = data  # The GUI provides the pre-loaded DataFrame

    def load(self):
        # Data is already loaded by the GUI, so we can skip this.
        pass

    def process(self):
        """
        The core logic of the module.
        """
        # Retrieve parameters provided by the user in the dialog, default to blank
        columns = self.params.get('columns', [])

        # Perform the data manipulation on a copy of the DataFrame
        processed_df = self.data.copy()
        for obj in columns:
            column, offset = obj['target_column'], obj['offset_value']
            # Verify the values are valid
            if not column or not offset:
                raise ValueError(f"A target column and offset value must be provided for all fields.")
            if column not in self.data.columns:
                raise ValueError(f"Column '{column}' not found in the data file.")
            # Offset the columns
            processed_df[column] = processed_df[column] + offset

        # Store the final result
        self.result = processed_df

    def save(self):
        """
        Saves the processed data.
        """
        if self.result is None: # This should never occur
            raise ValueError("Process method must be run before save.")
        
        # Determines output filename supplied
        output_filename = self.params.get('output_filename')
        if not output_filename:
            raise ValueError("Output filename must be specified.")

        # The base class provides a helper to save in the correct directory
        self.save_data(self.result, output_filename)

class OffsetSingleColumn(OffsetColumn):
    name = 'Offset Single Column'
    description = 'Offsets a single column by a specified value'

    PARAMETERS = [ # To override the default PARAMETERS list for the multi version
        ('target_column', 'Column to Offset', 'dropdown_column', True, None),
        ('offset_value', 'Offset Value', float, True, 'e.g., -1.25'),
        ('output_filename', 'Output Filename', str, True, 'offset_data.dat')
    ]

    def __init__(self, input_file, output_dir, params, data):
        # It's crucial to call the parent's __init__
        super().__init__(input_file, output_dir, params)
        self.data = data
        # We must adjust our parameters so that our parent class can process it.
        self.params['columns'] = [{'target_column': self.params['target_column'], 'offset_value': self.params['offset_value']}] # so it works with multi
```