from gui.manipulation_pipeline_widget import ManipulationModule
import pandas as pd

class Normalize(ManipulationModule):
    """Normalizes a column to the range [0, 1]."""
    name = "Normalize Column"
    description = "Scales selected column(s) to be between 0 and 1."

    PARAMETERS = []

    def process(self, df):
        for column in self.params.get('target_columns', []):
            min_val = df[column].min()
            max_val = df[column].max()
            range_val = max_val - min_val
            df[column] = (df[column] - min_val) / range_val if range_val != 0 else 0.5

        return df