from gui.manipulation_pipeline_widget import ManipulationModule
import numpy as np

class AverageLine(ManipulationModule):
    """Replaces all column data with its average, creating a horizontal line."""
    name = "Average Line"
    description = "Calculates the mean(s) of data columns and plots it as a horizontal line."

    PARAMETERS = []

    def process(self, df, full_plot_params=None):
        for column in self.params.get('target_columns'):
            df[column] = df[column].mean()

        return df