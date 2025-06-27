from gui.plot_module_widget import PlotModule
import matplotlib.pyplot as plt
import numpy as np
from logger import get_logger

logger = get_logger(__name__)

# Define the parameters for this module. The 'textarea' type will be multiline
PARAMETERS = [
    ('script_text', 'Custom Script', 'textarea', False,
     '# Example:\n# ax.set_title("My Custom Title")\n# ax.axvline(x=0, color=\'r\', linestyle=\'--\')'),
]


class CustomScriptModule(PlotModule):
    """
    Executes a custom Python script with access to the plot's figure and axes.
    Warning: Changes made by this script are not automatically undone when disabled.
    A full plot reset or re-applying other modules may be necessary to revert changes.
    """
    name = "Custom Script"
    description = "Run custom Python code with access to 'fig', 'ax', 'plt', and 'np'."
    PARAMETERS = PARAMETERS

    def __init__(self, params=None):
        super().__init__(params)
        self.script = self.params.get('script_text', '')

    def initialize(self):
        return True # Force a hard plot reset

    def plot(self, ax):
        """
        Executes the user-provided script in a controlled environment.
        """
        if not self.script or not self.script.strip():
            logger.debug("Custom script is empty or only contains comments. Skipping execution.")
            return

        fig = ax.figure

        # Create a controlled execution environment.
        # The script will have access to these variables.
        execution_scope = {
            'np': np,
            'plt': plt,
            'ax': ax,
            'fig': fig,
        }

        logger.info(f"Executing custom script:\n---\n{self.script}\n---")
        try:
            # Execute the script. Globals are empty for security.
            exec(self.script, {}, execution_scope)
        except Exception as e:
            logger.error(f"Error executing custom script: {e}", exc_info=True)
            # We could raise this to show a QMessageBox, but logging is less intrusive.

    def disable(self, ax):
        """
        This method cannot reliably undo arbitrary code execution.
        It serves as a placeholder and logs a warning.
        """
        logger.warning(f"Disabling '{self.name}' does not undo the executed script. "
                       "A plot reset or re-applying other modules may be necessary to override changes.")
        # No actions are taken as we cannot know what the script did.
