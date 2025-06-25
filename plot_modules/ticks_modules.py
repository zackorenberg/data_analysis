from gui.plot_module_widget import PlotModule
import matplotlib.pyplot as plt
from logger import get_logger

logger = get_logger(__name__)

SHARED_TICK_PARAM_DEFS = {
    'tick_values': ('Tick Values (csv)', str, False),
    'tick_labels': ('Tick Labels (csv)', str, False),

    'direction': ('Direction', ('in', 'out', 'inout'), False),
    'labelsize': ('Label Size', ('xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'), False),
    'labelcolor': ('Label Color', 'color', False),
    'color': ('Tick Color', 'color', False),

    'top': ('Show on Top', bool, False),
    'bottom': ('Show on Bottom', bool, False),
    'labeltop': ('Show Labels on Top', bool, False),
    'labelbottom': ('Show Labels on Bottom', bool, False),
    'left': ('Show on Left', bool, False),
    'right': ('Show on Right', bool, False),
    'labelleft': ('Show Labels on Left', bool, False),
    'labelright': ('Show Labels on Right', bool, False),

    'size': ('Size', float, False),
    'width': ('Width', float, False),
    'pad': ('Padding', float, False),
}


def _get_rc_param_default(axis, which, generic_key):
    """
    Helper to get the default rcParam value based on axis, which, and generic_key.
    Handles the inconsistencies in rcParam naming by checking specific keys first.
    """
    rc_prefix = f"{axis}tick"
    specific_key = f"{rc_prefix}.{which}.{generic_key}"
    general_key = f"{rc_prefix}.{generic_key}"

    # The global parameters overrides the local parameters so let's query that default instead
    # provided that the value is a boolean
    if general_key in plt.rcParams and plt.rcParams[general_key] in ['True', 'False', 'true', 'false', True, False, 't', 'f', 0, 1]:
        return plt.rcParams[general_key]


    # Try the most specific key first (e.g., 'xtick.major.size')
    if specific_key in plt.rcParams:
        #print(specific_key, plt.rcParams[specific_key])
        return plt.rcParams[specific_key]

    # Fallback to the general key (e.g., 'xtick.direction', 'xtick.top')
    if general_key in plt.rcParams:
        return plt.rcParams[general_key]

    logger.warning(f"rcParam key could not be resolved for {axis}_{which}_{generic_key}. Using None.")
    return None


def build_params_list(axis, which, *generic_keys):
    """
    Helper function to build a PARAMETERS list for a specific axis and tick type.
    It constructs the full parameter name and retrieves the default value from plt.rcParams.
    """
    result = []
    for generic_key in generic_keys:
        label_base, typ, required = SHARED_TICK_PARAM_DEFS[generic_key]

        full_param_name = f"{axis}_{which}_{generic_key}"
        ui_label = f"{axis.upper()} {which.capitalize()} {label_base}"

        # Special handling for manual tick values/labels
        if generic_key in ['tick_values', 'tick_labels']:
            full_param_name = f"{axis}_{which}_{generic_key}"
            ui_label = f"{axis.upper()} {which.capitalize()} {label_base}"
            default_value = ''
        else:
            default_value = _get_rc_param_default(axis, which, generic_key)
        result.append((full_param_name, ui_label, typ, required, default_value))
    return result


# The Skeleton Base Classes
class __BaseSingleAxisTickModule(PlotModule):
    """
    A base class that handles the logic for a single axis and tick type.
    Subclasses must define `axis` ('x' or 'y') and `which` ('major' or 'minor').
    """
    axis = None
    which = None

    def __init__(self, params=None):
        super().__init__(params)
        if not self.axis or not self.which:
            raise NotImplementedError("Subclasses of BaseSingleAxisTickModule must define 'axis' and 'which'.")

        # Prepare parameters for matplotlib functions
        self.tick_values = self._parse_csv_to_float(self.params.get(f'{self.axis}_{self.which}_tick_values'))
        self.tick_labels = self._parse_csv_to_str(self.params.get(f'{self.axis}_{self.which}_tick_labels'))

        self.tick_params_kwargs = {}
        for p_name, _, _, _, p_default in self.PARAMETERS:
            # Skip manual tick settings, which are handled separately
            if 'tick_values' in p_name or 'tick_labels' in p_name:
                continue
            #if 'color' in p_name and p_default in ['None', 'auto', 'inherit']:
            #    p_default = None
            # Lets try to not include a default, that way it doesn't automatically specify if the field is clear
            #value = self.params.get(p_name, p_default)
            value = self.params.get(p_name, None)
            if 'color' in p_name and value in ['None', 'auto', 'inherit']:
                value = None
            if value:
            # Extract the generic key (e.g., 'size' from 'x_major_size')
                generic_key = p_name.replace(f"{self.axis}_{self.which}_", "")
                self.tick_params_kwargs[generic_key] = value

    def plot(self, ax):
        """Applies the configured tick settings to the specified axis."""
        # Set manual tick values if provided
        set_ticks_func = getattr(ax, f'set_{self.axis}ticks')
        if self.tick_values is not None:
            set_ticks_func(self.tick_values, minor=(self.which == 'minor'))

        # Set manual tick labels if provided
        set_ticklabels_func = getattr(ax, f'set_{self.axis}ticklabels')
        if self.tick_labels is not None:
            set_ticklabels_func(self.tick_labels, minor=(self.which == 'minor'))

        # Apply all other appearance settings
        if self.tick_params_kwargs:
            for k,v in self.tick_params_kwargs.items():
                try:
                    ax.tick_params(axis=self.axis, which=self.which, **{k:v})
                except Exception as e:
                    logger.error(f"Could not set tick parameters '{k}' to value '{v}' for axis '{self.axis}': {e} ")
            #ax.tick_params(axis=self.axis, which=self.which, **self.tick_params_kwargs)

    def disable(self, ax):
        """Resets the tick settings for this module to their defaults."""
        # Reset locators to default
        axis_obj = getattr(ax, f'{self.axis}axis')
        if self.which == 'major':
            axis_obj.set_major_locator(plt.AutoLocator())
            ax.set_xticklabels([]) if self.axis == 'x' else ax.set_yticklabels([])
            for tick in axis_obj.get_major_ticks():
                tick.tick2line.set_visible(False) # Removes the extra top tick that doesnt go away
        else:  # minor
            axis_obj.set_minor_locator(plt.NullLocator())

        # Re-apply the default rcParams for this module's settings
        #default_kwargs = {p[0].replace(f"{self.axis}_{self.which}_", ""): p[4]
        #                  for p in self.PARAMETERS if 'tick_values' not in p[0] and 'tick_labels' not in p[0]}
        ax.tick_params(axis=self.axis, which=self.which, reset=True)
        # Reset top and left bug that occurs when dealing with majors
        ax.tick_params(axis='both', which='both', top=False, right=False)

    def _parse_csv_to_float(self, csv_string):
        if not csv_string: return None
        try:
            return [float(v.strip()) for v in csv_string.split(',') if v.strip()]
        except (ValueError, TypeError):
            logger.warning(f"Could not parse float CSV: '{csv_string}'")
            return None

    def _parse_csv_to_str(self, csv_string):
        if not csv_string: return None
        return [v.strip() for v in csv_string.split(',') if v.strip() is not None]



class __BaseMultiAxisTickModule(PlotModule):
    axis = ['x', 'y']
    which = ['major', 'minor']

    def __init__(self, params=None):
        super().__init__(params)

        self.modules = {
            'x':{'major': MajorXTickModule(params), 'minor': MinorXTickModule(params)},
            'y':{'major': MajorYTickModule(params), 'minor': MinorYTickModule(params)}
        }

    def plot(self, ax):
        for axis in self.axis:
            for which in self.which:
                self.modules[axis][which].plot(ax)

    def disable(self, ax):
        for axis in self.axis:
            for which in self.which:
                self.modules[axis][which].disable(ax)

tick_keys = {
    'x':{
        'major':[
           'tick_values', 'tick_labels', 'direction', 'labelsize', 'labelcolor', 'color',
           'top', 'bottom', 'labeltop', 'labelbottom', 'size', 'width', 'pad'
        ],
        'minor': [
            'tick_values', 'tick_labels', 'direction', 'color', 'top', 'bottom', 'size', 'width', 'pad'
        ]
    },
    'y':{
        'major':[
           'tick_values', 'tick_labels', 'direction', 'labelsize', 'labelcolor', 'color',
           'left', 'right', 'labelleft', 'labelright', 'size', 'width', 'pad'
        ],
        'minor': [
            'tick_values', 'tick_labels', 'direction', 'color', 'left', 'right', 'size', 'width', 'pad'
        ]
    },
}

# Actual tick modules

class MajorXTickModule(__BaseSingleAxisTickModule):
    name = "X Major Ticks"
    description = "Configures major ticks and labels for the X-axis."
    axis = 'x'
    which = 'major'
    PARAMETERS = build_params_list(axis, which, *tick_keys['x']['major'])
    DEFAULTS = {p[0]: p[4] for p in PARAMETERS}


class MinorXTickModule(__BaseSingleAxisTickModule):
    name = "X Minor Ticks"
    description = "Configures minor ticks for the X-axis."
    axis = 'x'
    which = 'minor'
    PARAMETERS = build_params_list(axis, which, *tick_keys['x']['minor'])
    DEFAULTS = {p[0]: p[4] for p in PARAMETERS}

    def plot(self, ax):
        ax.minorticks_on()
        super().plot(ax)

    def disable(self, ax):
        ax.minorticks_off()
        super().disable(ax)


class MajorYTickModule(__BaseSingleAxisTickModule):
    name = "Y Major Ticks"
    description = "Configures major ticks and labels for the Y-axis."
    axis = 'y'
    which = 'major'
    PARAMETERS = build_params_list(axis, which, *tick_keys['y']['major'])
    DEFAULTS = {p[0]: p[4] for p in PARAMETERS}


class MinorYTickModule(__BaseSingleAxisTickModule):
    name = "Y Minor Ticks"
    description = "Configures minor ticks for the Y-axis."
    axis = 'y'
    which = 'minor'
    PARAMETERS = build_params_list(axis, which,*tick_keys['y']['minor'])
    DEFAULTS = {p[0]: p[4] for p in PARAMETERS}

    def plot(self, ax):
        ax.minorticks_on() # Will turn on xaxis minor ticks as well
        super().plot(ax)

    def disable(self, ax):
        ax.minorticks_off()
        super().disable(ax)


class MajorMinorXTickModule(__BaseMultiAxisTickModule):
    name = "X Major/Minor Ticks"
    description = "Configures major and minor ticks and labels for the X-axis."
    axis = ['x']
    which = ['major', 'minor']
    PARAMETERS = [
        *build_params_list('x', 'major', *tick_keys['x']['major']),
        *build_params_list('x', 'minor',*tick_keys['x']['major']), # Provided we give values for majors, we can do the same extended values with minor
    ]
    def plot(self, ax):
        ax.minorticks_on() # Will turn on xaxis minor ticks as well
        super().plot(ax)

    def disable(self, ax):
        ax.minorticks_off()
        super().disable(ax)


class MajorMinorYTickModule(__BaseMultiAxisTickModule):
    name = "Y Major/Minor Ticks"
    description = "Configures major and minor ticks and labels for the Y-axis."
    axis = ['y']
    which = ['major', 'minor']
    PARAMETERS = [
        *build_params_list('y', 'major', *tick_keys['y']['major']),
        *build_params_list('y', 'minor', *tick_keys['y']['major']),
    ]
    def plot(self, ax):
        ax.minorticks_on() # Will turn on xaxis minor ticks as well
        super().plot(ax)

    def disable(self, ax):
        ax.minorticks_off()
        super().disable(ax)


"""
I am commenting this out until i have time to fix it

Basically, the problem is when trying to set ticks, it substitutes {which} in getattr which causes a problem.

The solution is to rewrite the __Base which is currently working after HOURS of debugging

class MajorBothTickModule(__BaseSingleAxisTickModule):
    name = "X/Y Major/Minor Ticks"
    description = "Configures major and minor ticks and labels for both axes."
    which='both'
    axis='both'
    PARAMETERS = sorted(set([
        *[(arg[0].replace('x', '').replace('major', '').strip(), arg[1].replace('X', '').replace('Major', '').strip(), *arg[2:]) for arg in build_params_list('x', 'major', *tick_keys['x']['major'])],
        *[(arg[0].replace('y', '').replace('major', '').strip(), arg[1].replace('Y', '').replace('Major', '').strip(), *arg[2:]) for arg in build_params_list('y', 'major', *tick_keys['y']['major'])],
    ]),key=lambda x:x[1])
"""