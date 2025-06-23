import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from logger import get_logger

logger = get_logger(__name__)

# Set some default rcParams
"""
matplotlib.rcParams.update({
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'lines.linewidth': 2,
    'figure.facecolor': '#232629',
    'axes.facecolor': '#232629',
    'axes.edgecolor': '#f0f0f0',
    'axes.labelcolor': '#f0f0f0',
    'xtick.color': '#f0f0f0',
    'ytick.color': '#f0f0f0',
    'text.color': '#f0f0f0',
    'legend.facecolor': '#35393b',
    'legend.edgecolor': '#f0f0f0',
})
"""
"""
plt.rcParams.update({
    'xtick.direction':'in',
    'axes.linewidth': 1,
    'lines.linewidth':1,
    'axes.labelsize': 24,
    'axes.titlesize':24,
    'ytick.direction':'in',
    'xtick.top': False,
    'xtick.bottom': True,
    'ytick.right': False,
    'ytick.left': True,
    'ytick.major.width':1.5,
    'xtick.major.width':1.5,
    'text.usetex':True,
    'xtick.major.pad': 5, #spacing between tick and label, moves axis label too
    'xtick.major.size': 7,
    'xtick.minor.pad': 5,
    'xtick.minor.size': 7,
    'ytick.major.pad': 5,
    'ytick.major.size': 7,
    'ytick.minor.pad': 5,
    'ytick.minor.size': 7,
    'legend.fontsize': 12,
    'font.family': 'sans-serif',
})
"""

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=11, height=8.5, dpi=300):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)

    def get_plot_params(self):
        axes = self.axes
        params = {
            'title': axes.get_title(),
            'xlabel': axes.get_xlabel(),
            'ylabel': axes.get_ylabel(),
            'xlim': axes.get_xlim(),
            'ylim': axes.get_ylim(),
            'grid': any(line.get_visible() for line in axes.get_xgridlines()) or any(line.get_visible() for line in axes.get_ygridlines()),
            'legend': axes.get_legend() is not None,
            'xticks': ','.join(str(x) for x in axes.get_xticks()),
            'yticks': ','.join(str(y) for y in axes.get_yticks()),
        }
        return params

    def apply_plot_params(self, params):
        self.axes.relim()
        self.axes.autoscale_view()
        # Set title
        self.axes.set_title(params.get('title', ''))
        # Set x/y labels
        self.axes.set_xlabel(params.get('xlabel', ''))
        self.axes.set_ylabel(params.get('ylabel', ''))
        # Set x/y limits
        xlim = params.get('xlim', (None, None))
        try:
            left = xlim[0] if xlim and len(xlim) > 0 and xlim[0] not in (None, '', 'None') else None
            right = xlim[1] if xlim and len(xlim) > 1 and xlim[1] not in (None, '', 'None') else None
            if left is not None and right is not None:
                self.axes.set_xlim(float(left), float(right))
            elif left is not None:
                self.axes.set_xlim(left=float(left))
            elif right is not None:
                self.axes.set_xlim(right=float(right))
            else:
                self.axes.set_xlim(auto=True)
        except Exception as e:
            logger.error(f"Error setting xlim: {xlim}, {e}")
        ylim = params.get('ylim', (None, None))
        try:
            bottom = ylim[0] if ylim and len(ylim) > 0 and ylim[0] not in (None, '', 'None') else None
            top = ylim[1] if ylim and len(ylim) > 1 and ylim[1] not in (None, '', 'None') else None
            if bottom is not None and top is not None:
                self.axes.set_ylim(float(bottom), float(top))
            elif bottom is not None:
                self.axes.set_ylim(bottom=float(bottom))
            elif top is not None:
                self.axes.set_ylim(top=float(top))
            else:
                self.axes.set_ylim(auto=True)
        except Exception as e:
            logger.error(f"Error setting ylim: {ylim}, {e}")
        # Set grid

        self.axes.grid(params.get('grid', False)) # Added reset=True to disable grid_module parameter overrides
        # Set x/y ticks
        xticks = params.get('xticks', '')
        if xticks:
            try:
                xtick_vals = [float(x.strip()) for x in xticks.split(',') if x.strip()]
                self.axes.set_xticks(xtick_vals)
            except Exception:
                pass
        yticks = params.get('yticks', '')
        if yticks:
            try:
                ytick_vals = [float(y.strip()) for y in yticks.split(',') if y.strip()]
                self.axes.set_yticks(ytick_vals)
            except Exception:
                pass
        # Set legend
        show_legend = params.get('legend', True)
        if show_legend:
            handles, labels = self.axes.get_legend_handles_labels()
            if handles and labels:
                self.axes.legend()
        else:
            legend = self.axes.get_legend()
            if legend is not None:
                legend.remove()

    @staticmethod
    def set_line_style_and_color(line, params):
        # Set color, linestyle, and marker if present in params, otherwise use matplotlib default
        color = params.get('color', None)
        if color:
            try:
                line.set_color(color)
            except Exception:
                pass  # Ignore invalid color
        linestyle = params.get('linestyle', None)
        if linestyle:
            try:
                line.set_linestyle(linestyle)
            except Exception:
                pass  # Ignore invalid linestyle
        marker = params.get('marker', None)
        if marker:
            try:
                line.set_marker(marker)
            except Exception:
                pass  # Ignore invalid marker


    def update_visuals(self, global_params, active_modules = []):
        """
        Applies all visual elements to the plot (global parameters, active modules, etc)

        This should be run after whatever plotting logic anywhere else in the code.

        :param global_params:
        :param active_modules:
        :return:
        """
        logger.debug(f"Updating visuals with {len(active_modules)} modules")

        self.apply_plot_params(global_params)

        for module in active_modules:
            try:
                logger.debug(f"Applying plot module: {module.name}")
                module.plot(self.axes)
            except Exception as e:
                logger.error(f"Error applying plot module {module.name}: {e}")

        self.figure.tight_layout()
        self.draw()
