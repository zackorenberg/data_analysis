from gui.manipulation_pipeline_widget import ManipulationModule

try:
    from scipy.signal import savgol_filter
except ImportError:
    savgol_filter = None

class SavgolFilter(ManipulationModule):
    """Applies a Savitzky-Golay filter to the Y-axis data."""
    name = "Savgol Filter"
    description = "Applies a Savitzky-Golay filter to the Y-axis data, smoothing it."

    PARAMETERS = [
        ('window_length', 'Window Length (odd)', int, True, 11),
        ('polyorder', 'Polynomial Order', int, True, 2),
    ]

    def __init__(self, params=None):
        super().__init__(params)
        if savgol_filter is None:
            raise ImportError("scipy is not installed. Please install it to use the Savgol Filter: pip install scipy")

    def process(self, df):

        for column in self.target_columns():
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found in DataFrame for Savgol filter.")

            df[column] = savgol_filter(df[column], self.params.get('window_length'), self.params.get('polyorder'))

        return df