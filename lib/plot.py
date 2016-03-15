
class TogglableLegend:
    def __init__(self, fig):
        self.fig = fig
        self.connection_id = fig.canvas.mpl_connect('pick_event', self.__onpick)
        self.__lines_legend = {}

    def add(self, legend_line, original_lines):
        if legend_line not in self.__lines_legend:
            self.__lines_legend[legend_line] = []
        self.__lines_legend[legend_line].extend(original_lines)
        legend_line.set_picker(5)  # 5 pts tolerance

    def __onpick(self, event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        legline = event.artist
        origlines = self.__lines_legend[legline]
        vis = not origlines[0].get_visible()
        for origline in origlines:
            origline.set_visible(vis)
        # Change the alpha on the line in the legend so we can see what lines
        # have been toggled
        if vis:
            legline.set_alpha(1.0)
        else:
            legline.set_alpha(0.4)
        self.fig.canvas.draw()
