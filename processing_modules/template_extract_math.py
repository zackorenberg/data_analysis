from processing_base import BaseProcessingModule
import numpy as np
import pandas as pd
import os
from logger import get_logger

logger = get_logger(__name__)

MODE = ['pre', 'post']

PARAMETERS = [
    ('columns_%d', 'Column', {
        'type': 'multi',
        'fields': [
            ('colname', 'Column Name', 'dropdown_column', True),
            ('expression', 'Expression', str, False, 'e.g. "(x-100)/100" or "*100"')
        ]
    }, True),
    ('prepend_date', 'Prepend Prefix', 'checkbox', False, True),
    ('file_name', 'File Name', str, True),
    ('output_folder', 'Subfolder Folder Name', str, False),
]

class ExtractColumnsWithMath(BaseProcessingModule):
    PARAMETERS = PARAMETERS

    def __init__(self, input_file, output_dir, params, data):
        super().__init__(input_file, output_dir, params)
        self.data = data  # DataFrame supplied by GUI

        print(input_file)
        print(output_dir)
        print(params)
        print(data)

    def load(self):
        pass  # Data is already loaded and supplied

    def process(self):
        logger.debug(f"Processing columns with math for file: {self.input_file}")
        col_entries = self.params.get('columns', [])
        if not isinstance(col_entries, list):
            col_entries = [col_entries]
        result = pd.DataFrame()
        for entry in col_entries:
            colname = entry.get('colname')
            expr = entry.get('expression', '').strip()
            if not colname or colname not in self.data.columns:
                logger.error(f"Column '{colname}' not found in input data.")
                raise ValueError(f"Column '{colname}' not found in input data.")
            x = self.data[colname]
            if expr:
                # Safe eval: only allow numpy and x
                np_env = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
                local_env = {'x': x}
                local_env.update(np_env)
                try:
                    y = eval(f"x{expr}" if expr.startswith(('/', '*', '+', '-')) else expr, {"__builtins__": {}}, local_env)
                except Exception as e:
                    logger.error(f"Error evaluating expression '{expr}' for column '{colname}': {e}")
                    raise ValueError(f"Error evaluating expression '{expr}' for column '{colname}': {e}")
                result[colname + (expr if expr else '')] = y
            else:
                result[colname] = x
        self.result = result

    def save(self):
        logger.debug(f"Saving processed columns for file: {self.input_file}")
        prefix = self.params.get('prefix', '')
        file_name = self.params.get('file_name', '')
        output_folder = self.params.get('output_folder', '')
        prepend_date = self.params.get('prepend_date', True)
        base_name = file_name
        if prepend_date and prefix:
            base_name = f"{prefix}_{base_name}"
        else:
            base_name = f"{base_name}_extracted"
        
        filename = f"{base_name}.dat"
        # Let the base module handle the output directory and cooldown
        self.save_data(self.result, filename, comments=None, metadata=None, subfolder=output_folder)
        logger.info(f"Saved processed columns to {filename}") 