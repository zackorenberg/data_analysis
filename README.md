# Data Analysis GUI

This application provides a graphical user interface for loading, visualizing, and processing scientific data, made with a focus on data from Corbino disk experiments. It allows for interactive plotting and the application of custom data processing routines through a modular system, with out-of-the-box support for LabGUI datafiles.

## Features

-   **Data Browsing**: A tabbed file browser for navigating raw, preprocessed, and postprocessed data directories.
-   **Interactive Plotting**: Double-click a data file to open a parameter dialog and plot various columns. Multiple data sets can be overlaid on the same axes.
-   **Global Plot Controls**: A dedicated panel to control global plot aesthetics like titles, labels, limits, and grids.
-   **Line Management**: A list of all plotted lines, allowing users to toggle visibility, edit parameters, or remove individual lines.
-   **Modular Data Processing**: A powerful, extensible system for applying custom data processing steps to your files.
-   **Configuration Management**:
    -   Save the current plot as a high-quality PDF.
    -   Export the configuration of all currently plotted lines (their source files and parameters) to a JSON file.
    -   Import a plot configuration to instantly recreate a previous plot.
    -   Append a plot configuration to an existing plot to overlay datasets.

## Data Processing

The application features a modular system that allows you to apply custom data processing scripts to your data files directly from the GUI.

-   **Discovery**: Processing modules are automatically discovered from the `processing_modules/` directory.
-   **Application**: Simply right-click on a data file in the "Data Browser" and select "Preprocess with..." or "Postprocess with..." to open a dialog.
-   **Configuration**: Each module can define its own set of parameters, which are dynamically rendered in the dialog, allowing for flexible and reusable processing workflows.

For a detailed guide on how to create your own custom processing modules, please see the **`processing_modules/README.md`** file.

## Installation and First-Run

1.  Clone the repository.
2.  Install the required dependencies from `requirements.txt`.
3.  Launch the application with command `python main.py` in the root directory.