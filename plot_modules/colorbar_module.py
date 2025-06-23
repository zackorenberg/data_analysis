from gui.plot_module_widget import PlotModule


class ColorbarModule(PlotModule):
    """Adds a colorbar to plots"""
    name = "Colobar Module"
    description = "Adds a colorbar to plots with customizable position and label"

    def __init__(self):
        super().__init__()
        self.colorbar_label = "Value"
        self.colorbar_position = 'right'
        self.colorbar_fraction = 0.046
        self.colorbar_pad = 0.04
    
    def plot(self, ax):
        """Add colorbar to the plot"""
        # Check if there are any mappable objects (like scatter plots with color)
        mappable = None
        for collection in ax.collections:
            if hasattr(collection, 'get_array') and collection.get_array() is not None:
                mappable = collection
                break
        
        if mappable is not None:
            cbar = plt.colorbar(mappable, ax=ax, fraction=self.colorbar_fraction, pad=self.colorbar_pad)
            cbar.set_label(self.colorbar_label)
