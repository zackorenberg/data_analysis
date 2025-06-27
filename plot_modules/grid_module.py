from gui.plot_module_widget import PlotModule
import matplotlib.pyplot as plt
# Define the parameters that the user can configure


PARAMETERS = [
    # (name, label, type, required, default_value)
    ('grid_alpha', 'Alpha', float, False, plt.rcParams['grid.alpha']),
    ('grid_style', 'Style', ('-', '--', '-.', ':'), False, plt.rcParams['grid.linestyle']),
    ('grid_color', 'Color', 'color', True, plt.rcParams['grid.color']),
    ('grid_lw', 'Linewidth', float, False, plt.rcParams['grid.linewidth']),
    ('grid_axes', 'Axes', ('both', 'x', 'y'), False, plt.rcParams['axes.grid.axis']),
    ('grid_which', 'Which', ('both', 'major', 'minor'), False, plt.rcParams['axes.grid.which'])
]

# Note, Future rcparam widget will not change these. It would be a good idea to make setting rcparams reload all plot modules
DEFAULTS = {name:default for name,_,_,_,default in PARAMETERS}

class GridModule(PlotModule):
    """Adds a grid to plots"""
    name = "Grid Module"
    description = "Adds a customizable grid to plots with configurable style and alpha"

    def __init__(self, params=None):
        super().__init__(params)
        # Use the passed-in params, falling back to defaults
        self.grid_alpha = self.params.get('grid_alpha', 0.8)
        self.grid_style = self.params.get('grid_style', '-')
        self.grid_color = self.params.get('grid_color', 'gray')
        self.grid_axes = self.params.get('grid_axes', 'both')
        self.grid_which = self.params.get('grid_which', 'major')
        self.grid_lw = self.params.get('grid_lw', 1.0)

    def plot(self, ax):
        """Add grid to the plot using configured parameters"""
        ax.grid(True, alpha=self.grid_alpha, linestyle=self.grid_style, color=self.grid_color, which=self.grid_which, axis=self.grid_axes, linewidth=self.grid_lw)

    def disable(self, ax):
        """Reset the grid parameters which get saved when calling the grid function in plot()"""
        ax.grid(alpha = DEFAULTS['grid_alpha'], linestyle=DEFAULTS['grid_style'], color=DEFAULTS['grid_color'], which=DEFAULTS['grid_which'], axis=DEFAULTS['grid_axes'], linewidth=DEFAULTS['grid_lw'])