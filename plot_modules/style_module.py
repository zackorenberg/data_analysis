from gui.plot_module_widget import PlotModule
import matplotlib.pyplot as plt
from logger import get_logger

logger = get_logger(__name__)
available_styles = plt.style.available

PARAMETERS = [
    # (name, label, type, required, default_value)
    ('style_name', 'Plot Style', tuple(available_styles), True, 'default'),
]


# --- 3. Create the StyleModule class ---
class StyleModule(PlotModule):
    """
    Applies a global Matplotlib plot style.

    Note: This changes the global style for all plots. It is highly
    recommended to click 'Reload' on the Plot Modules widget after
    applying a new style to update the default values in other modules.
    """
    name = "Plot Style"
    description = "Applies a Matplotlib plot style (e.g., 'ggplot', 'seaborn'). Affects all plots. It is highly recommended to click 'Reload' on Plot Modules after changing the style."
    PARAMETERS = PARAMETERS

    def __init__(self, params=None):
        super().__init__(params)
        # Store the selected style name. Fallback to 'default' if not provided.
        self.style_name = self.params.get('style_name', 'default')

        # To ensure a clean reversion, we capture a copy of the 'default' style's
        # rcParams when the module is instantiated.
        with plt.style.context('default'): # THis will fuck with rcparam module for sure
            self._default_rc_params = plt.rcParams.copy()

    def plot(self, ax):
        """
        Apply the selected style globally.
        This is a global change, so it doesn't just affect the passed 'ax'.
        The main application will handle redrawing the canvas, which will now use the new style.
        """
        try:
            # Applying the style will change the current plt.rcParams for the entire application.
            plt.style.use(self.style_name)
            logger.info(f"Applied global plot style: '{self.style_name}'")
            # After applying, it's a good idea to force a reload of other modules' defaults.
            # The user should be encouraged to use the "Reload" button in the PlotModuleWidget.
        except Exception as e:
            logger.error(f"Failed to apply style '{self.style_name}': {e}")

    def disable(self, ax):
        """
        Revert the global style to Matplotlib's default configuration.
        """
        try:
            # Revert to the captured default parameters.
            # Using rc.update is the correct way to apply a dictionary of settings.
            plt.rcParams.update(self._default_rc_params)
            logger.info("Reverted plot style to Matplotlib default.")
        except Exception as e:
            logger.error(f"Failed to revert style to default: {e}")
