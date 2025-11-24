from gui.manipulation_pipeline_widget import ManipulationModule


class SortValues(ManipulationModule):
    """Applies a Savitzky-Golay filter to the Y-axis data."""
    name = "Sorts values by columns"
    description = 'write me'

    PARAMETERS = []

    def process(self, df):

        sort_columns = self.target_columns()
        if sort_columns:
            df.sort_values(by=sort_columns, inplace=True)

        return df