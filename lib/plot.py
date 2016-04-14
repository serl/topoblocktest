import warnings
# the other imports are inside functions!!!1


def import_matplotlib(interactive=True):
    if interactive:
        import matplotlib
        matplotlib.use('qt4agg')
    import matplotlib.pyplot as plt
    return plt


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


def throughput_cpu(columns, rows_grouped, x_title='', style_fn=None):
    if len(rows_grouped) == 0:
        raise ValueError('Nothing to plot')
    if style_fn is None:
        style_fn = lambda row_element, group_id: {}
    # import
    from collections import OrderedDict
    plt = import_matplotlib()

    fig, axes = plt.subplots(len(rows_grouped), 2, sharex=True)
    if len(rows_grouped) == 1:
        axes = (axes,)
    togglable_legend = TogglableLegend(fig)
    row_id = 0
    for (ax_throughput, ax_cpu) in axes:
        while row_id not in rows_grouped:
            row_id += 1
        lines = []
        for label, rowdetails in rows_grouped[row_id].items():
            row = rowdetails['row']
            row_element = None  # used for the style_fn
            x_values = []
            throughput_values = []
            throughput_error = []
            cpu_values = []
            cpu_error = []
            for i, col in enumerate(columns):
                r = row[i]
                if r is None:
                    # warnings.warn("Missing value on serie '{}' for x value {}".format(label, col), RuntimeWarning)
                    continue
                row_element = r
                throughput_values.append(r['iperf_result']['throughput'][0])
                throughput_error.append(r['iperf_result']['throughput'][1])
                cpu_values.append(100 - r['iostat_cpu']['idle'][0])  # 100 - idle
                cpu_error.append(r['iostat_cpu']['idle'][1])
                x_values.append(col)
            basestyle = {'linestyle': '-', 'markersize': 7}
            kwargs = basestyle.copy()
            kwargs.update(style_fn(row_element, row_id))
            series_lines = []
            line, two, three = ax_throughput.errorbar(x_values, throughput_values, yerr=throughput_error, label=label, **kwargs)
            series_lines.extend((line,) + two + three)
            line, two, three = ax_cpu.errorbar(x_values, cpu_values, yerr=cpu_error, label=label, **kwargs)
            series_lines.extend((line,) + two + three)
            lines.append(series_lines)
        ax_throughput.set_xlabel(x_title)
        ax_throughput.set_ylabel('throughput (b/s)')
        ax_throughput.grid(True)
        ax_cpu.set_xlabel(x_title)
        ax_cpu.set_ylabel('cpu utilization (%)')
        ax_cpu.grid(True)
        ax_cpu.axis([None, None, 10, 105])

        legend = ax_cpu.legend(bbox_to_anchor=(1, 1), loc=2, fontsize='x-small')
        for legline, origlines in zip(legend.get_texts(), lines):
            togglable_legend.add(legline, origlines)
        row_id += 1

    plt.subplots_adjust(left=0.05, right=0.82, top=0.95, bottom=0.1)
    plt.show()
