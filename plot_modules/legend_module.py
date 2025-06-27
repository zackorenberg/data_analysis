from gui.plot_module_widget import PlotModule
import matplotlib.pyplot as plt

#for k,v in plt.rcParams.items():
#    if 'legend' in k:
#        print(k,v)
# Define the parameters that the user can configure
PARAMETERS = [
    # (name, label, type, required, default_value)
    ('legend_loc', 'Location', ('best', 'upper right', 'upper left', 'lower left', 'lower right',
                                  'right', 'center left', 'center right', 'lower center', 'upper center', 'center'), False, plt.rcParams['legend.loc']),
    ('legend_fontsize', 'Font Size', ( 'xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'), False, plt.rcParams['legend.fontsize']),
    ('legend_frameon', 'Show Frame', bool, False, plt.rcParams['legend.frameon']),
    ('legend_framealpha', 'Frame Alpha', float, False, plt.rcParams['legend.framealpha']),
    ('legend_fancybox', 'Fancy Box', bool, False, plt.rcParams['legend.fancybox']),
    ('legend_shadow', 'Shadow', bool, False, plt.rcParams['legend.shadow']),
    ('legend_ncol', 'Number of Columns', int, False, 1),
    ('legend_title', 'Title', str, False, ''),
    ('legend_title_fontsize', 'Title Font Size',  ('xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'), False, plt.rcParams['legend.title_fontsize']),
    ('legend_markerscale', 'Marker Scale', float, False, plt.rcParams['legend.markerscale']),
    ('legend_numpoints', 'Number of Points', int, False, plt.rcParams['legend.numpoints']),
    ('legend_labelspacing', 'Label Spacing', float, False, plt.rcParams['legend.labelspacing']),
    ('legend_handlelength', 'Handle Length', float, False, plt.rcParams['legend.handlelength']),
    ('legend_handletextpad', 'Handle-Text Pad', float, False, plt.rcParams['legend.handletextpad']),
    ('legend_columnspacing', 'Column Spacing', float, False, plt.rcParams['legend.columnspacing']),
    ('legend_labelcolor', 'Label Color', 'color', False, plt.rcParams['legend.labelcolor']),
    ('legend_borderpad', 'Border Pad', float, False, plt.rcParams['legend.borderpad']),
    ('legend_borderaxespad', 'Border-Axes Pad', float, False, plt.rcParams['legend.borderaxespad']),
    ('legend_edgecolor', 'Edge Color', 'color', False, plt.rcParams['legend.edgecolor']),
    ('legend_facecolor', 'Face Color', 'color', False, plt.rcParams['legend.facecolor']),
    ('legend_handleheight', 'Handle Height', float, False, plt.rcParams['legend.handleheight']),
    ('legend_scatterpoints', 'Scatter Points', int, False, plt.rcParams['legend.scatterpoints']),
]

# Store default values for resetting
DEFAULTS = {name: default for name, _, _, _, default in PARAMETERS}

class LegendModule(PlotModule):
    """Adds a legend to plots with extensive customization"""
    name = "Legend Module"
    description = "Adds a highly customizable legend to plots"
    PARAMETERS = PARAMETERS

    def __init__(self, params=None):
        super().__init__(params)
        # Use the passed-in params, falling back to defaults
        self.legend_params = {name.replace('legend_', ''): self.params.get(name, DEFAULTS[name]) for name in DEFAULTS}
        # Special handling for title font size
        if self.legend_params.get('title_fontsize') is None:
            self.legend_params.pop('title_fontsize')

    def plot(self, ax):
        """Add legend to the plot using configured parameters"""
        ax.legend(**self.legend_params)

    def disable(self, ax):
        """Remove the legend when the module is disabled"""
        if ax.get_legend() is not None:
            ax.get_legend().remove()