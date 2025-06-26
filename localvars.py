import os
import json

# --- Default Settings ---
# These are the initial values if no settings file is found.
# The structure here defines the default values and the hierarchy.
DEFAULT_SETTINGS = {
    "data_dirs": {
        "raw": os.path.join('data', 'raw'),
        "preprocessed": os.path.join('data', 'preprocessed'),
        "postprocessed": os.path.join('data', 'postprocessed'),
        "plots": os.path.join('data', 'plots'),
    },
    "behavior_flags": {
        "reread_datafile_on_edit": False,
    },
    "caching": {  # Renamed from plot_module_caching to be more general
        "plot_modules": {
            "enable": False,
            "cache_file": "plot_modules_cache.json",
        },
        "plotted_data": {
            "enable": False,
            "cache_file": "plotted_data_cache.json",
        },
        # Add other modules here that can be cached
        # "other_module_caching": {
        #     "enable": False,
        #     "cache_file": "other_module_cache.json",
        # },
    },
    "default_plot_config_file": "plot_config.json",
    "default_plot_save_path": os.path.join('data', 'plots', 'plot.pdf'),
    "processing_modules_dir": "processing_modules",
}

# --- Settings UI Metadata ---
# This dictionary defines how each setting appears in the UI and its behavior.
# Keys are dot-separated paths corresponding to keys in DEFAULT_SETTINGS.
# 'label': Display name in the UI.
# 'type': Widget type ('directory_path', 'checkbox', 'string', 'integer', 'float').
# 'restart_required': True if changing this setting requires an application restart.
SETTINGS_METADATA = {
    "data_dirs.raw": {"label": "Raw Data Directory", "type": "directory_path", "restart_required": True},
    "data_dirs.preprocessed": {"label": "Preprocessed Data Directory", "type": "directory_path",
                               "restart_required": True},
    "data_dirs.postprocessed": {"label": "Postprocessed Data Directory", "type": "directory_path",
                                "restart_required": True},
    "data_dirs.plots": {"label": "Plots Output Directory", "type": "directory_path", "restart_required": True},

    "behavior_flags.reread_datafile_on_edit": {"label": "Re-read data file on edit (slower)", "type": "checkbox",
                                               "restart_required": True},

    "caching.plot_modules.enable": {"label": "Enable caching of Plot Module configurations", "type": "checkbox",
                                    "restart_required": False},
    "caching.plot_modules.cache_file": {"label": "Plot Module Cache File Name", "type": "string",
                                        "restart_required": False},
    "caching.plotted_data.enable": {"label": "Enable caching of Plotted Data", "type": "checkbox",
                                    "restart_required": False},
    "caching.plotted_data.cache_file": {"label": "Plotted Data Cache File Name", "type": "string",
                                        "restart_required": False},
    # Add metadata for other caching options here if they are added to DEFAULT_SETTINGS
    # "caching.other_module_caching.enable": {"label": "Enable Other Module Caching", "type": "checkbox", "restart_required": False},
    # "caching.other_module_caching.cache_file": {"label": "Other Module Cache File Name", "type": "string", "restart_required": False},
}

# --- Caching Modules Registry ---
# This maps a caching key (from DEFAULT_SETTINGS['caching']) to the actual
# import/export *method names* for that module's configuration.
# 'widget_instance_attr': The attribute name in MainWindow to get the widget instance.
CACHING_MODULES_REGISTRY = {
    "plot_modules": {
        "import_method_name": "import_module_config",  # Just the method name
        "export_method_name": "export_module_config",  # Just the method name
        "widget_instance_attr": "plot_module_widget",  # Attribute name in MainWindow to get the widget instance
    },
    "plotted_data": {
        "import_method_name": "import_plot_config",  # Method on MainWindow
        "export_method_name": "export_plot_config",  # Method on MainWindow
        "widget_instance_attr": "self",  # The MainWindow instance itself
    },
    # Add other cacheable modules here
    # "other_module_caching": {
    #     "import_method_name": "import_config",
    #     "export_method_name": "export_config",
    #     "widget_instance_attr": "other_module_widget_instance_in_mainwindow",
    # },
}

# --- Settings File Path ---
SETTINGS_DIRECTORY = "settings"
SETTINGS_FILE = "settings.json"

# --- Internal Functions for Settings Management ---
_current_settings = {}


def _get_nested_value(d, keys):
    """Helper to get a value from a nested dictionary using a list of keys."""
    if not keys:
        return d
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None  # Or raise KeyError
    return current


def _set_nested_value(d, keys, value):
    """Helper to set a value in a nested dictionary using a list of keys."""
    if not keys:
        return  # Cannot set root
    current = d
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            current[key] = value
        else:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]


def _load_settings():
    """Loads settings from the SETTINGS_FILE, merging with defaults."""
    global _current_settings
    if not os.path.exists(SETTINGS_DIRECTORY):
        os.makedirs(SETTINGS_DIRECTORY)
    if os.path.exists(os.path.join(SETTINGS_DIRECTORY,SETTINGS_FILE)):
        try:
            with open(os.path.join(SETTINGS_DIRECTORY,SETTINGS_FILE), 'r') as f:
                loaded_settings = json.load(f)
            # Merge with defaults to ensure all keys exist (for new settings added later)
            _current_settings = _deep_merge_dicts(DEFAULT_SETTINGS.copy(), loaded_settings)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode {SETTINGS_FILE}. Using default settings.")
            _current_settings = DEFAULT_SETTINGS.copy()
            _save_settings()  # Save defaults if file was corrupted
    else:
        _current_settings = DEFAULT_SETTINGS.copy()
        _save_settings()  # Create settings file with defaults


def _save_settings():
    """Saves the current settings to the SETTINGS_FILE."""
    with open(os.path.join(SETTINGS_DIRECTORY, SETTINGS_FILE), 'w') as f:
        json.dump(_current_settings, f, indent=4)


def _deep_merge_dicts(default_dict, user_dict):
    """Recursively merges user_dict into default_dict."""
    merged = default_dict.copy()
    for key, value in user_dict.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


# Load settings when localvars.py is imported
_load_settings()

# --- Expose Settings as Global Variables ---
# These variables will be used throughout your application.
# They are dynamically populated from _current_settings.
# Access them via _get_nested_value for consistency.

# Data directories
RAW_DATA_DIR = _get_nested_value(_current_settings, ["data_dirs", "raw"])
PREPROCESSED_DATA_DIR = _get_nested_value(_current_settings, ["data_dirs", "preprocessed"])
POSTPROCESSED_DATA_DIR = _get_nested_value(_current_settings, ["data_dirs", "postprocessed"])
PLOTS_DIR = _get_nested_value(_current_settings, ["data_dirs", "plots"])

# Behavior flags
REREAD_DATAFILE_ON_EDIT = _get_nested_value(_current_settings, ["behavior_flags", "reread_datafile_on_edit"])

# Caching settings (for direct use in mainapplication)
# Note: These are specific to plot_modules caching, but the framework supports more.
PLOT_MODULE_CACHING_ENABLED = _get_nested_value(_current_settings, ["caching", "plot_modules", "enable"])
PLOT_MODULE_CACHE_FILE = _get_nested_value(_current_settings, ["caching", "plot_modules", "cache_file"])

# Other general settings
DEFAULT_PLOT_CONFIG = _get_nested_value(_current_settings, ["default_plot_config_file"])
DEFAULT_PLOT_SAVE = _get_nested_value(_current_settings, ["default_plot_save_path"])
PROCESSING_MODULES_DIR = _get_nested_value(_current_settings, ["processing_modules_dir"])

# Any other constants can be added here (if not configurable via settings)
DATA_DELIMITER = '  '


# Function to update and save settings from the dialog
def update_and_save_settings(new_settings_dict):
    """
    Updates the internal _current_settings and saves them to file.
    This function is called by the SettingsDialog.
    """
    global _current_settings
    _current_settings = new_settings_dict
    _save_settings()

    # Re-populate global variables to reflect new settings immediately
    global RAW_DATA_DIR, PREPROCESSED_DATA_DIR, POSTPROCESSED_DATA_DIR, PLOTS_DIR
    global REREAD_DATAFILE_ON_EDIT
    global PLOT_MODULE_CACHING_ENABLED, PLOT_MODULE_CACHE_FILE
    global DEFAULT_PLOT_CONFIG, DEFAULT_PLOT_SAVE, PROCESSING_MODULES_DIR

    # Does this really work though ?
    RAW_DATA_DIR = _get_nested_value(_current_settings, ["data_dirs", "raw"])
    PREPROCESSED_DATA_DIR = _get_nested_value(_current_settings, ["data_dirs", "preprocessed"])
    POSTPROCESSED_DATA_DIR = _get_nested_value(_current_settings, ["data_dirs", "postprocessed"])
    PLOTS_DIR = _get_nested_value(_current_settings, ["data_dirs", "plots"])
    REREAD_DATAFILE_ON_EDIT = _get_nested_value(_current_settings, ["behavior_flags", "reread_datafile_on_edit"])
    PLOT_MODULE_CACHING_ENABLED = _get_nested_value(_current_settings, ["caching", "plot_modules", "enable"])
    PLOT_MODULE_CACHE_FILE = _get_nested_value(_current_settings, ["caching", "plot_modules", "cache_file"])
    DEFAULT_PLOT_CONFIG = _get_nested_value(_current_settings, ["default_plot_config_file"])
    DEFAULT_PLOT_SAVE = _get_nested_value(_current_settings, ["default_plot_save_path"])
    PROCESSING_MODULES_DIR = _get_nested_value(_current_settings, ["processing_modules_dir"])


def get_current_settings():
    """Returns a deep copy of the current settings."""
    return json.loads(json.dumps(_current_settings))  # Simple deep copy using JSON


def get_caching_method_name(module_key, func_type):
    """
    Returns the method name (string) for a caching function.
    func_type can be 'import_method_name' or 'export_method_name'.
    """
    if module_key not in CACHING_MODULES_REGISTRY:
        return None
    return CACHING_MODULES_REGISTRY[module_key].get(func_type)


def get_widget_instance_attr(module_key):
    """Returns the attribute name for the widget instance in MainWindow."""
    return CACHING_MODULES_REGISTRY[module_key].get("widget_instance_attr")



""" Old localvars before dynamic settings were implemented
import os

# Data directories
RAW_DATA_DIR = os.path.join('data', 'raw')
PREPROCESSED_DATA_DIR = os.path.join('data', 'preprocessed')
POSTPROCESSED_DATA_DIR = os.path.join('data', 'postprocessed')
PLOTS_DIR = os.path.join('data', 'plots')

# Processing modules directory
PROCESSING_MODULES_DIR = 'processing_modules'

# Default file names/paths
DEFAULT_PLOT_CONFIG = 'plot_config.json'
DEFAULT_PLOT_SAVE = os.path.join(PLOTS_DIR, 'plot.pdf')

# Reading/writing data file formats
DATA_DELIMITER = '  '

# Behaviour flags
REREAD_DATAFILE_ON_EDIT = False

# Any other constants can be added here
"""
