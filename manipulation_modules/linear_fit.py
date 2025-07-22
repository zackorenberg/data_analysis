from gui.manipulation_pipeline_widget import ManipulationModule
import numpy as np
from logger import get_logger

logger = get_logger(__name__)

try:
    from scipy.stats import linregress
except:
    linregress = None

def str_with_err(val, err): # Modified from stackoverflow
    """String with value and error in parenthesis with the number of digits given by precision."""
    if err == 0:
        return f'{val}'
    unc_exp = -int(np.floor(np.log10(abs(err))))
    leading_digit = int(abs(err) * 10 ** unc_exp)
    second_leading_digit = int(
        10*(abs(err) * 10 ** (unc_exp)) - 10*int(abs(err) * 10 ** (unc_exp))
    )
    precision = 2 if leading_digit == 1 and second_leading_digit != 0 else 1

    # Number of digits in the error
    err_decimals = precision - int(np.floor(np.log10(err) + 1))
    # Output error with a "precision" number of significant digits
    err_out = round(err, err_decimals)
    # Removes leading zeros for fractional errors
    if err_out < 1:
        err_out = int(round(err_out * 10**err_decimals))
        err_format = 0
    else:
        err_format = int(np.clip(err_decimals, 0, np.inf))

    # Format the value to have the same significant digits as the error
    val_out = round(val, err_decimals)
    val_format = int(np.clip(err_decimals, 0, np.inf))

    return f'{val_out:.{val_format}f}({err_out:.{err_format}f})'

class LinearFit(ManipulationModule):

    name = 'Linear Fit'
    description = 'Replaces target column(s) with a linear least-squares fit against a specified column'

    PARAMETERS = [
        ('x_column', 'X-axis Column', 'dropdown_column', True),
        ('print_fit', 'Print Fit Parameters', 'checkbox', False, True)
    ]

    def __init__(self, params = None):
        super().__init__(params)
        if linregress is None: # We'll do it with numpy
            def linfit(x, y):
                coef, V = np.polyfit(x, y, 1, cov=True)
                return tuple(coef), tuple(np.sqrt(np.diag(V)))
        else:
            def linfit(x, y):
                out = linregress(x,y)
                return (out.slope, out.intercept), (out.stderr, out.intercept_stderr)
        self.linfit = linfit





    def process(self, df):
        print_fit = self.params.get('print_fit', False)

        xcol = self.params.get('x_column')
        if xcol is None or xcol not in df.columns:
            raise ValueError(f"Invalid X-axis Column supplied: {xcol}")
        x = df[xcol]

        for column in self.target_columns():
            (slope, intercept), (dslope, dintercept) = self.linfit(x, df[column])
            df[column] = slope*x + intercept
            logger.info(f"Applied linear fit to '{column}' using '{xcol}'")
            if print_fit:
                print(f"Linear fit of '{column}' using '{xcol}':")
                print("\tSlope: %s"%str_with_err(slope, dslope))
                print("\tIntercept: %s"%str_with_err(intercept, dintercept))

        return df