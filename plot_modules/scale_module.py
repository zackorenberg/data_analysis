### WIP

from gui.plot_module_widget import PlotModule
from matplotlib.scale import get_scale_names
from logger import get_logger

logger = get_logger(__name__)

# These are the strings accepted by ax.set_xscale() and ax.set_yscale()
AVAILABLE_SCALE_TYPES = get_scale_names() #('linear', 'log', 'symlog', 'logit')

# Define the parameters that the user can configure for axis scaling
PARAMETERS = [
    # (name, label, type, required, default_value)
    ('x_scale_type', 'X-Axis Scale', AVAILABLE_SCALE_TYPES, False, 'linear'),
    ('y_scale_type', 'Y-Axis Scale', AVAILABLE_SCALE_TYPES, False, 'linear'),
]


class ScaleModule(PlotModule):
    """
    Modifies the scale type of the X and Y axes (e.g., linear, logarithmic, symlog, logit).
    """
    name = "Axis Scale"
    description = "Changes the scale type of the X and Y axes (e.g., linear, logarithmic)."
    PARAMETERS = PARAMETERS

    def __init__(self, params=None):
        super().__init__(params)
        self.x_scale_type = self.params.get('x_scale_type', 'linear')
        self.y_scale_type = self.params.get('y_scale_type', 'linear')


    def plot(self, ax):
        """
        Applies the selected scale types to the X and Y axes.
        This also implicitly sets the appropriate tick locator and formatter.
        For example, 'log' scale uses a LogLocator, while 'linear' uses an AutoLocator.
        """
        # Apply X-axis scale
        try:
            if ax.get_xscale() != self.x_scale_type:
                ax.set_xscale(self.x_scale_type)
                logger.debug(f"Set X-axis scale to: '{self.x_scale_type}'")
        except ValueError as e:
            logger.error(f"Error setting X-axis scale to '{self.x_scale_type}': {e}. "
                         "Ensure data is positive for 'log' scales, or consider 'symlog' for data crossing zero.")
        except Exception as e:
            logger.error(f"Unexpected error setting X-axis scale to '{self.x_scale_type}': {e}")

        # Apply Y-axis scale
        try:
            if ax.get_yscale() != self.y_scale_type:
                ax.set_yscale(self.y_scale_type)
                logger.debug(f"Set Y-axis scale to: '{self.y_scale_type}'")
        except ValueError as e:
            logger.error(f"Error setting Y-axis scale to '{self.y_scale_type}': {e}. "
                         "Ensure data is positive for 'log' scales, or consider 'symlog' for data crossing zero.")
        except Exception as e:
            logger.error(f"Unexpected error setting Y-axis scale to '{self.y_scale_type}': {e}")

    def disable(self, ax):
        """
        It should automatically be default unless specified otherwise
        """
