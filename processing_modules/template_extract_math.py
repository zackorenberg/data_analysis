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
            ('expression', 'Expression', str, False)
        ]
    }, True),
    ('output_folder', 'Output Folder Name', str, True),
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
        output_folder = self.params['output_folder']
        cooldown = self.get_cooldown_name()
        outdir = os.path.join(self.output_dir, cooldown, output_folder)
        os.makedirs(outdir, exist_ok=True)
        outpath = os.path.join(outdir, f"{os.path.splitext(os.path.basename(self.input_file))[0]}_extracted.txt")
        try:
            self.save_data(self.result, outpath)
            logger.info(f"Saved processed columns to {outpath}")
        except Exception as e:
            logger.error(f"Error saving processed columns to {outpath}: {e}")
            raise 