import argparse
import json
import os
import sys
from pprint import pformat

# --- STANDALONE CONFIGURATION ---
# To run this script without any command-line arguments, set the paths below.
# If a path is set to None, the script will prompt for it.
DEFAULT_CONFIG_FILE = 'flipchip_tmo3_params.json'  # Example: "C:/tests/my_offset_test.json"
DEFAULT_INPUT_FILE = 'data/raw/25B1_Tr/250714_TMO3_4ptResistance_TimeTrace_10nA__I=TR1-BR1_V=TR2-BR2__002.dat'   # Example: "C:/data/raw/cooldown1/sample.dat"

# Add project root to path to allow for local imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox

from DataManagement.data_reader import read_data_file
from DataManagement.module_loader import discover_modules
from gui.processing_dialog import ProcessingDialog
from localvars import PROCESSING_MODULES_DIR
from logger import get_logger

logger = get_logger("GuiProcessingTester")


def run_gui_test(config_path, input_path):
    """
    Runs a GUI test on the ProcessingDialog. It populates the dialog's widgets
    from a config file, reads the values back, and verifies they match.
    """
    logger.info(f"--- Starting GUI test with config: {config_path} ---")
    logger.info(f"--- Using input data file: {input_path} ---")

    # 1. Start a QApplication - This is essential for any GUI testing.
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # 2. Load configuration and determine module mode
    with open(config_path, 'r') as f:
        config = json.load(f)

    module_name = config.get('module')
    if not module_name:
        raise ValueError("Config file must contain a 'module' key.")

    all_modules = discover_modules(PROCESSING_MODULES_DIR, 'all')
    target_module_info = next(((name, cls) for name, cls, _ in all_modules if name == module_name or getattr(cls, 'name', None) == module_name), None)
    if not target_module_info:
        raise ValueError(f"Module '{module_name}' not found.")

    _, module_class = target_module_info
    module_mode = getattr(module_class, 'MODE', 'pre')
    if isinstance(module_mode, list):
        module_mode = module_mode[0]

    # 3. Get data columns, which are needed to instantiate the dialog
    df, _, _, _ = read_data_file(input_path)
    columns = list(df.columns)

    # 4. Instantiate the ProcessingDialog
    logger.info(f"Creating ProcessingDialog for module '{module_name}' in '{module_mode}' mode.")
    dialog = ProcessingDialog(file_path=input_path, module_type=module_mode, data_columns=columns)

    # 5. Programmatically interact with the dialog
    
    # A. Select the module in the module-selection QComboBox.
    #    This assumes the combo box has the object name 'module_combo'.
    module_combo = dialog.findChild(QComboBox, 'module_combo')
    if not module_combo:
        # Provide a more helpful error message for debugging.
        all_combos = dialog.findChildren(QComboBox)
        combo_names = [f"'{c.objectName()}'" if c.objectName() else "(No Name)" for c in all_combos]
        msg = (
            "Could not find a QComboBox named 'module_combo' in ProcessingDialog.\n\n"
            "To fix this, find the QComboBox responsible for module selection in 'gui/processing_dialog.py' "
            "and set its object name, like this:\n\n"
            "    self.my_module_combo.setObjectName('module_combo')\n\n"
            f"Available QComboBoxes found in the dialog: {', '.join(combo_names) or 'None'}"
        )
        raise NotImplementedError(msg)
    module_combo.setCurrentText(module_name)
    logger.info(f"Programmatically selected module: '{module_combo.currentText()}'")
    app.processEvents() # Allow the UI to update and create parameter widgets

    # B. Set parameter values using the dialog's test helper method.
    #    This assumes a method `set_ui_from_params` exists in ProcessingDialog.
    params_to_set = config.get('params', {})
    if not hasattr(dialog, 'set_ui_from_params'):
        raise NotImplementedError("ProcessingDialog is missing the 'set_ui_from_params' method needed for testing.")
    
    logger.info("Setting UI widgets from config params...")
    dialog.set_ui_from_params(params_to_set)
    app.processEvents()

    # C. Get the parameters back from the GUI widgets
    logger.info("Reading parameters back from UI widgets...")
    _, _, params_from_gui = dialog.get_selected_module()

    # 6. Compare results and report
    
    # Normalize input dict values to string for fair comparison (except bools)
    normalized_params_to_set = {
        k: v if isinstance(v, bool) else str(v)
        for k, v in params_to_set.items()
    }

    logger.debug(f"Normalized Input Params:\n{pformat(normalized_params_to_set)}")
    logger.debug(f"Params Read from GUI:\n{pformat(params_from_gui)}")

    if normalized_params_to_set == params_from_gui:
        logger.info("--- SUCCESS: Parameters from GUI match input parameters. ---")
        return True
    else:
        logger.error("--- FAILURE: Parameters from GUI do not match input parameters. ---")
        # You can add a more detailed diff here if you install a library like deepdiff
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run a GUI test on a processing module using a JSON config file.")
    parser.add_argument("--config", dest="config_file", help="Path to the JSON config file. Overrides DEFAULT_CONFIG_FILE.")
    parser.add_argument("--input", dest="input_file", help="Path to the input data file. Overrides all other sources.")
    args = parser.parse_args()

    # --- Determine Config File Path ---
    config_path = args.config_file or DEFAULT_CONFIG_FILE
    while not config_path or not os.path.exists(config_path):
        if config_path:
            print(f"\nError: Configuration file not found at '{config_path}'")
        config_path_input = input("Please enter the path to the JSON configuration file: ").strip().strip('\'"')
        if not config_path_input:
            print("Operation cancelled."); sys.exit(0)
        config_path = config_path_input

    # --- Determine Input Data File Path ---
    input_path = args.input_file or DEFAULT_INPUT_FILE
    if not input_path:
        with open(config_path, 'r') as f:
            input_path = json.load(f).get('input_file')

    while not input_path or not os.path.exists(input_path):
        if input_path:
            print(f"\nError: Input data file not found at '{input_path}'")
        input_path_input = input("Please enter the path to the input data file: ").strip().strip('\'"')
        if not input_path_input:
            print("Operation cancelled."); sys.exit(0)
        input_path = input_path_input

    try:
        run_gui_test(config_path, input_path)
    except Exception:
        logger.error(f"--- Test FAILED with an exception for {config_path} ---", exc_info=True)
        raise

if __name__ == "__main__":
    main()