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