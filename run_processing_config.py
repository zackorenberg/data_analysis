import argparse
import json
import os
import sys

# --- STANDALONE CONFIGURATION ---
# Set this path to a test configuration file to run the script from PyCharm
# If set to None, the script will prompt you
DEFAULT_CONFIG_FILE = None
# Example: DEFAULT_CONFIG_FILE = "path/to/your/test_config.json"
DEFAULT_INPUT_FILE = None
# Example: DEFAULT_INPUT_FILE = "path/to/your/data_file.dat"

# Lets just assume that this is in the root directory so we can import stuff (StackOverflow)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from DataManagement.data_reader import read_data_file
from DataManagement.module_loader import discover_modules
from localvars import PROCESSING_MODULES_DIR, PREPROCESSED_DATA_DIR, POSTPROCESSED_DATA_DIR
from logger import get_logger

logger = get_logger("ProcessingTester")


def extract_cooldown(file_path):
    """Extracts the cooldown name from a file path, mimicking GUI logic."""
    parts = os.path.normpath(file_path).split(os.sep)
    for key in ('raw', 'preprocessed', 'postprocessed'):
        try:
            idx = parts.index(key)
            if idx + 1 < len(parts):
                return parts[idx + 1]
        except ValueError:
            continue
    return ''


def run_test(config, input_path = None):
    """
    Runs a processing module test based on a JSON configuration file.
    This script does not catch exceptions from the module's process/save
    methods, allowing them to fail loudly for debugging purposes.
    """

    module_name = config.get('module')
    input_file = input_path or config.get('input_file') # Does not necessarily be in the json unless added explicitly
    params = config # we are going to use exported params for this!

    if not module_name or not input_file:
        raise ValueError("Config file must contain 'module' and 'input_file' keys.")

    logger.info(f"Module to test: '{module_name}'")
    logger.info(f"Input data file: '{input_file}'")

    if not os.path.exists(input_file):
        logger.error(f"Input data file specified in config not found: {input_file}")
        raise FileNotFoundError(f"Input data file specified in config not found: {input_file}")

    # 2. Discover available modules to find the target
    all_modules = discover_modules(PROCESSING_MODULES_DIR, 'all')

    target_module_info = next(((name, cls) for name, cls, _ in all_modules if name == module_name or getattr(cls, 'name', None) == module_name), None)

    if not target_module_info:
        raise ValueError(f"Module '{module_name}' not found in '{PROCESSING_MODULES_DIR}'.")

    _, module_class = target_module_info
    logger.info(f"Found module class: {module_class.__name__}")

    # 3. Prepare module inputs
    df, _, _, _ = read_data_file(input_file)
    logger.info(f"Successfully loaded data from '{input_file}'. Shape: {df.shape}")

    # Determine output directory based on the module's MODE attribute
    module_mode = getattr(module_class, 'MODE', 'pre')
    if isinstance(module_mode, list):
        module_mode = module_mode[0]  # Default to the first mode if multiple are specified

    if module_mode == 'pre':
        output_dir = PREPROCESSED_DATA_DIR
    elif module_mode == 'post':
        output_dir = POSTPROCESSED_DATA_DIR
    else:
        raise ValueError(f"Unknown module mode '{module_mode}' for module '{module_name}'")
    logger.info(f"Module mode is '{module_mode}', output directory set to '{output_dir}'")

    # Add cooldown to params
    if 'cooldown' not in params:
        params['cooldown'] = extract_cooldown(input_file)
        logger.info(f"Automatically added 'cooldown': '{params['cooldown']}' to params.")

    # Instantiate the module
    logger.info("Instantiating module...")
    module_instance = module_class(input_file=input_file, output_dir=output_dir, params=params, data=df)
    logger.info("Module instantiated successfully.")

    # Run load
    logger.info("Running load()...")
    module_instance.load()
    logger.info("load() completed.")

    # Run processing
    logger.info("Running process()...")
    module_instance.process()
    logger.info("process() completed.")

    # Run save
    logger.info("Running save()...")
    module_instance.save()
    logger.info("save() completed.")



def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run a processing module test from a JSON config file.")
    parser.add_argument("--config", dest="config_file", help="Path to the JSON configuration file for the test.")
    args = parser.parse_args()

    config_path = args.config_file or DEFAULT_CONFIG_FILE



    # If no config path is found, interactively ask the user for it.
    while not config_path or not os.path.exists(config_path):
        if config_path:  # Path was given but file does not exist
            print(f"\nError: Configuration file not found at '{config_path}'")

        config_path_input = input("Please enter the path to the JSON configuration file: ").strip()
        if not config_path_input:
            print("Operation cancelled.")
            sys.exit(0)
        config_path = config_path_input.strip('\'"')  # Handle quotes from drag-and-drop in supported tty


    logger.info(f"--- Starting test with config ---")
    with open(config_path, 'r') as f:
        config = json.load(f)

    input_path = config.get('input_file') or DEFAULT_INPUT_FILE  # input_file isnt in json by default, check anyways

    while not input_path or not os.path.exists(input_path):
        if input_path:  # Path was given but file does not exist
            print(f"\nError: Input file not found at '{input_path}'")

        input_path_input = input("Please enter the path to the input data file: ").strip()
        if not input_path_input:
            print("Operation cancelled.")
            sys.exit(0)
        input_path = input_path_input.strip('\'"')  # Handle quotes from drag-and-drop in supported tty

    try:
        run_test(config, input_path)
    except Exception:
        logger.error(f"--- Test FAILED for {config_path} ---", exc_info=True)
        # Re-raise the exception to get the full traceback in the console after notifying user
        raise


    logger.info(f"--- Test completed successfully for {config_path} ---")

if __name__ == "__main__":
    main()