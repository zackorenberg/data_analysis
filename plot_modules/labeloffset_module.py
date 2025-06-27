from gui.plot_module_widget import PlotModule
import re

# TODO: add paremeters?
class LabelOffset(PlotModule):
    name = 'Label Offset'
    description = 'Automatically add the order of magnitude to the axis labels'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ax = None
        self.cids = [] # Callback IDs to cancel on redraw

    def __offset_to_latex(self, offset):
        if offset == '':
            return ''
        float_str = offset if 'e' in offset else "{0:.2g}".format(float(offset))
        if "e" in float_str:
            try:
                base, exponent = float_str.replace(u"\u2212", "-").split("e")
                if int(base) != 1: # just incase its 0.99999 or something
                    return r"[x${0} \times 10^{{{1}}}$]".format(base, int(float(exponent)))
                else:
                    return r"[$\times 10^{{{0}}}$]".format(int(float(exponent)))
            except:
                return float_str
        else:
            return float_str

    def plot(self, ax):

        if self.ax is not ax:
            # Disconnect previous callbacks
            if self.ax is not None:
                for cid in self.cids:
                    self.ax.callbacks.disconnect(cid)
            self.ax = ax
            self.cids = [
                self.ax.callbacks.connect('xlim_changed', self.update),
                self.ax.callbacks.connect('ylim_changed', self.update)
            ]

        self.update(None)


    def update(self, artist = None): # What to do with artist ??
        if self.ax is None:
            return

        offset_pattern = re.compile(r"\s\[.*\\times\s10\^\{.*\}\$\]$")
        for axis in ['xaxis', 'yaxis']:
            axis = getattr(self.ax, axis)
            label = axis.get_label().get_text()
            label = offset_pattern.sub('', label) # Remove any previous offset

            fmt = axis.get_major_formatter()
            offset_str = self.__offset_to_latex(fmt.get_offset())

            if label and offset_str:
                axis.offsetText.set_visible(False)
                axis.set_label_text(f"{label} {offset_str}")

    def disable(self, ax):
        if self.ax:
            for cid in self.cids:
                self.ax.callbacks.disconnect(cid)
            self.cids = []
            self.ax = None
