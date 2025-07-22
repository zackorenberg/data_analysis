import numpy as np
from gui.manipulation_pipeline_widget import ManipulationModule

# Attempt to import curve_fit from scipy
try:
    from scipy.optimize import curve_fit
except ImportError:
    curve_fit = None

exec_str = f'''
global _function
def _function(x, %s): 
    return %s
'''
_function = None

class CurveFitExpression(ManipulationModule):
    """
    Perform a curve fit on target columns
    """

    name = "Curve Fit (Expression)"
    description = "Replaces target column(s) with a curve fit against a specified column from a user expression"

    PARAMETERS = [
        ('x_column', 'X-axis Column', 'dropdown_column', True),
        ('variables_%d', 'Variables', str, True, 'a'),
        ('expression', 'Expression', str, True, 'a*x**2 + b*x + c')
    ]

    def __init__(self, params=None):
        super().__init__(params)
        if curve_fit is None:
            raise ImportError("scipy is not installed. Please install it to use Curve Fit: pip install scipy")
        self.np_env =  {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
        self.np_env['np'] = np

    def build_function(self, expression, parameters):
        #exec(exec_str%(", ".join(parameters), expression), globals(), self.np_env.copy())
        # return _function
        local_env = {} #self.np_env.copy()
        exec(f'''def fit_function(x, {", ".join(parameters)}): return {expression}''', self.np_env, local_env)
        return local_env['fit_function']


    def process(self, df):
        print_fit = self.params.get('print_fit', False)

        xcol = self.params.get('x_column')
        if xcol is None or xcol not in df.columns:
            raise ValueError(f"Invalid X-axis Column supplied: {xcol}")
        x = df[xcol]

        parameters = self.params.get('variables', [])
        expression = self.params.get('expression')

        if not parameters:
            raise ValueError("Parameters must be supplied to perform a curve fit")
        if not expression:
            raise ValueError("Expression must be supplied to perform a curve fit")

        try:
            func = self.build_function(expression, parameters)
            for column in self.target_columns():
                popt, pcov = curve_fit(func, x, df[column])
                df[column] = func(x, *popt)
                perr = np.sqrt(np.diag(pcov))

                print(f"Applied curve fit to '{column}' using '{xcol}'")
                if print_fit:
                    for param, val, err in zip(parameters, popt, perr):
                        print("\t" + f"{param} = {val} +/- {err}")

        except Exception as e:
            print(f"Failed to curve fit with error: {e}")
            raise e


        return df




class CurveFitFunction(ManipulationModule):
    """
    Perform a curve fit on target columns
    """

    name = "Curve Fit (Custom Function)"
    description = "Replaces target column(s) with a curve fit against a specified column from a user expression"

    PARAMETERS = [
        ('x_column', 'X-axis Column', 'dropdown_column', True),
        ('function', 'Function', 'textarea', True, '''# Your function goes here
def fit_function(x, a, b, c):
    return a*x**2 + b*x + c
''')
    ]

    def __init__(self, params=None):
        super().__init__(params)
        if curve_fit is None:
            raise ImportError("scipy is not installed. Please install it to use Curve Fit: pip install scipy")
        self.np_env = {k: getattr(np, k) for k in dir(np) if not k.startswith('_')}
        self.np_env['np'] = np

    def build_function(self, funct_str):
        #exec("global _function\n" + funct_str + "\n_function = fit_function", globals(), self.np_env)
        local_env = {}
        exec(funct_str, self.np_env, local_env) #self.np_env)
        return local_env['fit_function'] if 'fit_function' in local_env else next(v for k,v in local_env.items() if k not in self.np_env)

    def process(self, df):
        print_fit = self.params.get('print_fit', False)

        xcol = self.params.get('x_column')
        if xcol is None or xcol not in df.columns:
            raise ValueError(f"Invalid X-axis Column supplied: {xcol}")
        x = df[xcol]

        funct = self.params.get('function')

        if not funct:
            raise ValueError("Function must be supplied to perform a curve fit")


        try:
            func = self.build_function(funct)
            for column in self.target_columns():
                popt, pcov = curve_fit(func, x, df[column])
                df[column] = func(x, *popt)
                perr = np.sqrt(np.diag(pcov))

                print(f"Applied curve fit to '{column}' using '{xcol}'")
                if print_fit:
                    for param, (val, err) in enumerate(zip(popt, perr)):
                        print("\t" + f"{param} = {val} +/- {err}")

        except Exception as e:
            print(f"Failed to curve fit with error: {e}")
            raise e

        return df
