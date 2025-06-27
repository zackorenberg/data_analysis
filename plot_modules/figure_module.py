from gui.plot_module_widget import PlotModule
import matplotlib.pyplot as plt
from logger import get_logger

logger = get_logger(__name__)

# Define the parameters that the user can configure for the figure and axes
PARAMETERS = [
    # (name, label, type, required, default_value)

    # --- Figure-level parameters ---
    ('figure_facecolor', 'Figure Face Color', 'color', False, plt.rcParams['figure.facecolor']),
    ('figure_edgecolor', 'Figure Edge Color', 'color', False, plt.rcParams['figure.edgecolor']),

    # --- Axes-level parameters ---
    ('axes_facecolor', 'Axes Face Color', 'color', False, plt.rcParams['axes.facecolor']),
    ('axes_edgecolor', 'Axes Spine Color', 'color', False, plt.rcParams['axes.edgecolor']),
    ('axes_linewidth', 'Axes Spine Linewidth', float, False, plt.rcParams['axes.linewidth']),
    ('axes_labelcolor', 'Axes Label Color', 'color', False, plt.rcParams['axes.labelcolor']),
    ('axes_titlecolor', 'Title Color', 'color', False, plt.rcParams['axes.titlecolor']),

    # --- Global X-Tick Parameters ---
    ('xtick_direction', 'X-Tick Direction', ('in', 'out', 'inout'), False, plt.rcParams['xtick.direction']),
    ('xtick_color', 'X-Tick Color', 'color', False, plt.rcParams['xtick.color']),
    ('xtick_labelsize', 'X-Tick Label Size', ('xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'),
     False, plt.rcParams['xtick.labelsize']),
    ('xtick_labelcolor', 'X-Tick Label Color', 'color', False, plt.rcParams['xtick.labelcolor']),
    ('xtick_top', 'Show Top X-Ticks', bool, False, plt.rcParams['xtick.top']),
    ('xtick_bottom', 'Show Bottom X-Ticks', bool, False, plt.rcParams['xtick.bottom']),
    ('xtick_labeltop', 'Show Top X-Labels', bool, False, plt.rcParams['xtick.labeltop']),
    ('xtick_labelbottom', 'Show Bottom X-Labels', bool, False, plt.rcParams['xtick.labelbottom']),

    # --- Global Y-Tick Parameters ---
    ('ytick_direction', 'Y-Tick Direction', ('in', 'out', 'inout'), False, plt.rcParams['ytick.direction']),
    ('ytick_color', 'Y-Tick Color', 'color', False, plt.rcParams['ytick.color']),
    ('ytick_labelsize', 'Y-Tick Label Size', ('xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'),
     False, plt.rcParams['ytick.labelsize']),
    ('ytick_labelcolor', 'Y-Tick Label Color', 'color', False, plt.rcParams['ytick.labelcolor']),
    ('ytick_left', 'Show Left Y-Ticks', bool, False, plt.rcParams['ytick.left']),
    ('ytick_right', 'Show Right Y-Ticks', bool, False, plt.rcParams['ytick.right']),
    ('ytick_labelleft', 'Show Left Y-Labels', bool, False, plt.rcParams['ytick.labelleft']),
    ('ytick_labelright', 'Show Right Y-Labels', bool, False, plt.rcParams['ytick.labelright']),
]


class FigureModule(PlotModule):
    """
    Controls global visual parameters of the figure and axes,
    such as background colors, spine properties, and global tick styles.
    """
    name = "Figure/Axes Style"
    description = "Controls global figure/axes colors, line properties, and general tick appearance."
    PARAMETERS = PARAMETERS

    def __init__(self, params=None):
        super().__init__(params)
        # Capture the rcParams defaults *at the time this instance is created*
        self._initial_rc_params = {}
        for name, _, _, _, _ in self.PARAMETERS:
            # Most parameter names map directly to rcParams keys by replacing '_' with '.'
            rc_key = name.replace('_', '.')
            try:
                self._initial_rc_params[name] = plt.rcParams[rc_key]
            except KeyError:
                logger.warning(f"Could not find rcParam for '{name}' using key '{rc_key}'.")
                self._initial_rc_params[name] = None

    def _get_revert_color(self, param_name):
        """
        Determines the correct color value to revert to.
        If the initial rcParam was 'None', 'inherit', or 'auto', return None.
        Otherwise, return the captured color value.
        """
        initial_value = self._initial_rc_params.get(param_name)
        if isinstance(initial_value, str) and initial_value.lower() in ['none', 'inherit', 'auto']:
            return None
        return initial_value

    def plot(self, ax):
        """Apply figure and axes styling."""
        fig = ax.figure

        # --- Apply Figure-level Parameters ---
        fig.set_facecolor(self.params.get('figure_facecolor'))
        fig.set_edgecolor(self.params.get('figure_edgecolor'))

        # --- Apply Axes-level Parameters ---
        ax.set_facecolor(self.params.get('axes_facecolor'))

        # Apply spine color and width
        for spine in ax.spines.values():
            spine.set_edgecolor(self.params.get('axes_edgecolor'))
            spine.set_linewidth(self.params.get('axes_linewidth'))

        # Apply label and title colors
        ax.xaxis.label.set_color(self.params.get('axes_labelcolor'))
        ax.yaxis.label.set_color(self.params.get('axes_labelcolor'))
        ax.title.set_color(self.params.get('axes_titlecolor'))

        # --- Apply Global Tick Parameters ---
        x_tick_params = {k.replace('xtick_', ''): v for k, v in self.params.items() if k.startswith('xtick_')}
        y_tick_params = {k.replace('ytick_', ''): v for k, v in self.params.items() if k.startswith('ytick_')}

        if x_tick_params:
            ax.tick_params(axis='x', which='both', **x_tick_params)
        if y_tick_params:
            ax.tick_params(axis='y', which='both', **y_tick_params)

    def disable(self, ax):
        """Revert figure and axes styling to the rcParams defaults captured at module instantiation."""
        fig = ax.figure

        # Revert figure properties using the smart color reversion
        fig.set_facecolor(self._get_revert_color('figure_facecolor'))
        fig.set_edgecolor(self._get_revert_color('figure_edgecolor'))

        # Revert axes properties
        ax.set_facecolor(self._get_revert_color('axes_facecolor'))

        # Revert spines
        for spine in ax.spines.values():
            spine.set_edgecolor(self._get_revert_color('axes_edgecolor'))
            spine.set_linewidth(self._initial_rc_params.get('axes_linewidth'))

        # Revert labels and title
        ax.xaxis.label.set_color(self._get_revert_color('axes_labelcolor'))
        ax.yaxis.label.set_color(self._get_revert_color('axes_labelcolor'))
        ax.title.set_color(self._get_revert_color('axes_titlecolor'))

        # Revert global tick parameters
        default_x_params = {
            k.replace('xtick_', ''): self._get_revert_color(k) if 'color' in k else self._initial_rc_params.get(k)
            for k in self._initial_rc_params if k.startswith('xtick_')
        }
        default_y_params = {
            k.replace('ytick_', ''): self._get_revert_color(k) if 'color' in k else self._initial_rc_params.get(k)
            for k in self._initial_rc_params if k.startswith('ytick_')
        }

        if default_x_params:
            ax.tick_params(axis='x', which='both', **default_x_params)
        if default_y_params:
            ax.tick_params(axis='y', which='both', **default_y_params)
