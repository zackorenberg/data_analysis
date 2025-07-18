# In processing_modules/showcase_module.py

from processing_base import BaseProcessingModule
import pprint  # To pretty print the output

# Set MODE to appear in both pre- and post-processing menus for easy access.
MODE = ['pre', 'post']

# This PARAMETERS list is a showcase of all supported widget types.
PARAMETERS = [
    # =========================================================================
    # 1. Simple Top-Level Parameters
    # These are the most basic parameter types.
    # =========================================================================
    ('a_string_param', 'Simple Text', str, True, 'Enter some text here'),
    ('an_integer_param', 'Simple Integer', int, False, 123),
    ('a_float_param', 'Simple Float', float, False, 3.14),
    ('a_boolean_param', 'Simple Checkbox', bool, False, True),
    ('a_label', 'Info Label', 'label', False, 'This is a non-editable label.'),

    # =========================================================================
    # 2. Dropdown (ComboBox) Examples
    # =========================================================================
    ('column_dropdown', 'Select Data Column', 'dropdown_column', True),
    ('fixed_dropdown', 'Select Fixed Option', ('Option A', 'Option B', 'Option C'), True),

    # =========================================================================
    # 3. Multi-Value Parameter (Repeatable Simple Field)
    # The `_%d` suffix on the name signals that this is a repeatable field.
    # The form will collect all values into a single list.
    # e.g., params['tags'] = ['tag1', 'tag2']
    # =========================================================================
    ('tags_%d', 'List of Tags', str, False),

    # =========================================================================
    # 4. Static (Single) Group
    # A dictionary `type` with a 'fields' key creates a non-repeatable QGroupBox.
    # This is for visually organizing related parameters.
    # e.g., params['static_group'] = {'field_1': 'alpha', 'field_2': False}
    # =========================================================================
    ('static_group', 'Static Settings Group', {
        'fields': [
            ('field_in_static_group', 'Field 1', str, False, 'alpha'),
            ('another_field', 'Field 2 (bool)', bool, False, False),
        ]
    }, False),

    # =========================================================================
    # 5. Multi-Group (Repeatable Group of Fields)
    # A dictionary `type` with a 'fields' key AND the `_%d` suffix on the name
    # creates a repeatable QGroupBox with its own add/remove controls.
    # This is for complex list-based parameters.
    # e.g., params['multi_group'] = [
    #           {'filter_column': 'Vx', 'filter_value': 1.0, ...},
    #           {'filter_column': 'Vy', 'filter_value': 2.5, ...}
    #       ]
    # =========================================================================
    ('multi_group_%d', 'Repeatable Filter Group', {
        'fields': [
            ('filter_column', 'Filter on Column', 'dropdown_column', True),
            ('filter_mode', 'Filter Mode', ('greater than', 'less than', 'equal to'), True),
            ('filter_value', 'Filter Value', float, True),

            # --- 5a. NESTED STATIC GROUP ---
            # You can nest static groups inside any other group for more structure.
            # The parameters will be collected into a nested dictionary.
            # e.g., ...'nested_static_group': {'nested_text': 'gamma', ...}
            ('nested_static_group', 'Nested Advanced Options', {
                'fields': [
                    ('nested_text', 'Nested Text', str, False, 'gamma'),
                    ('nested_bool', 'Nested Checkbox', bool, False, True)
                ]
            }, False),

            # --- 5b. NESTED MULTI-GROUP ---
            # You can even nest a repeatable group inside another repeatable group.
            # This will create a list of lists of dictionaries.
            # e.g., ...'nested_multi_group': [{'name': 'a', 'val': 1}, {'name': 'b', 'val': 2}]
            ('nested_multi_group_%d', 'Nested Repeatable Sub-items', {
                'fields': [
                    ('sub_item_name', 'Sub-Item Name', str, True),
                    ('sub_item_value', 'Sub-Item Value', int, True)
                ]
            }, False)
        ]
    }, False)
]


class ShowcaseModule(BaseProcessingModule):
    """
    A module demonstrating all available parameter types for testing and as a
    developer example. This module does not process or save data; it only
    prints the parameters it receives to the console.
    """
    name = "Parameter Showcase"
    description = "A test module to display all parameter types."

    def __init__(self, input_file, output_dir, params, data):
        super().__init__(input_file, output_dir, params)
        # Data is not used in this example, but it's passed by the GUI
        self.data = data

    def process(self):
        """
        Instead of processing data, this module prints the received parameters
        to the console to verify that they are being collected correctly.
        """
        print("\n" + "="*20)
        print(" ShowcaseModule Parameters Received ")
        print("="*20 + "\n")

        # Using pprint for a clean, readable output of the params dictionary
        pprint.pprint(self.params)

        print("\n" + "="*20)
        print(" End of ShowcaseModule Parameters ")
        print("="*20 + "\n")

        # In a real module, you would set self.result to a processed DataFrame.
        # Here, we set it to None as we are not producing an output file.
        self.result = None

    def save(self):
        """
        This module does not save any data. In a real module, you would call
        self.save_data(self.result, 'output_filename.dat') here.
        """
        print("ShowcaseModule: 'save' method called. No data to save.")
        pass
