import warnings
# the other imports are inside functions!!!1


def import_matplotlib(interactive=True):
    if interactive:
        import matplotlib
        matplotlib.use('qt4agg')
    import matplotlib.pyplot as plt
    return plt


def format_list(values, divisor=1000):
    powers = ['', 'K', 'M', 'G', 'T', 'P']
    div_values = values.copy()
    power = powers[0]
    while max(div_values) >= divisor:
        div_values = [x / divisor for x in div_values]
        power = powers[powers.index(power) + 1]
    return div_values, power


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


class YAx:

    @classmethod
    def get_instance(cls, attr_name):
        if attr_name == 'throughput':
            return ThroughputAx()
        elif attr_name == 'cpu':
            return CpuAx()
        elif attr_name == 'packetput':
            return PacketputAx()

    def get_value(self, r):
        raise ValueError('Must be implemented in subclass')

    def format_ax(self, ax):
        pass


class ThroughputAx(YAx):

    def get_value(self, r):
        return r['iperf_result']['throughput']

    def format_ax(self, ax):
        formatted_locs, power = format_list(ax.get_yticks())
        ax.set_yticklabels(map("{0:.0f}".format, formatted_locs))
        ax.set_ylabel('throughput ({}b/s)'.format(power))
        ax.grid(True)


class CpuAx(YAx):

    def get_value(self, r):
        return (100 - r['iostat_cpu']['idle'][0], r['iostat_cpu']['idle'][1])  # 100 - idle

    def format_ax(self, ax):
        ax.set_ylabel('cpu utilization (%)')
        ax.grid(True)
        ax.axis([None, None, 10, 105])


class PacketputAx(YAx):

    def get_value(self, r):
        return r['iperf_result']['packetput']

    def format_ax(self, ax):
        formatted_locs, power = format_list(ax.get_yticks())
        ax.set_yticklabels(map("{0:.0f}".format, formatted_locs))
        ax.set_ylabel('throughput ({}pps)'.format(power))
        ax.grid(True)


def dynamic(columns, rows_grouped, y_axes, x_title='', style_fn=None):
    if len(rows_grouped) == 0 or len(y_axes) == 0:
        raise ValueError('Nothing to plot')
    for i, y_ax in enumerate(y_axes):
        if isinstance(y_ax, str):
            y_axes[i] = YAx.get_instance(y_ax)
    if style_fn is None:
        style_fn = lambda row_element, group_id: {}
    # import
    from collections import OrderedDict
    plt = import_matplotlib()

    fig, all_axes = plt.subplots(len(rows_grouped), len(y_axes), sharex=True)
    if len(rows_grouped) == 1:
        all_axes = (all_axes,)
    togglable_legend = TogglableLegend(fig)
    row_id = 0
    for axes_row in all_axes:
        while row_id not in rows_grouped:
            row_id += 1
        lines = []
        for label, rowdetails in rows_grouped[row_id].items():
            row = rowdetails['row']
            row_element = None  # used for the style_fn

            # fill the data structures
            x_values = [[] for i in range(len(y_axes))]
            plot_values = [[] for i in range(len(y_axes))]
            plot_errors = [[] for i in range(len(y_axes))]
            for col_index, col_name in enumerate(columns):
                r = row[col_index]
                if r is None:
                    # warnings.warn("Missing value on serie '{}' for x value {}".format(label, col), RuntimeWarning)
                    continue
                row_element = r
                for y_ax_index, y_ax in enumerate(y_axes):
                    value_error = y_ax.get_value(r)
                    if value_error is None:
                        continue
                    if not isinstance(value_error, tuple):
                        value_error = (value_error, 0)
                    plot_values[y_ax_index].append(value_error[0])
                    plot_errors[y_ax_index].append(value_error[1])
                    x_values[y_ax_index].append(col_name)

            # draw plot
            basestyle = {'linestyle': '-', 'markersize': 7}
            kwargs = basestyle.copy()
            kwargs.update(style_fn(row_element, row_id))
            series_lines = []
            for y_ax_index, mpl_ax in enumerate(axes_row):
                y_ax = y_axes[y_ax_index]
                line, two, three = mpl_ax.errorbar(x_values[y_ax_index], plot_values[y_ax_index], yerr=plot_errors[y_ax_index], label=label, **kwargs)
                series_lines.extend((line,) + two + three)
                mpl_ax.set_xlabel(x_title)
                y_ax.format_ax(mpl_ax)
            lines.append(series_lines)

        legend = mpl_ax.legend(bbox_to_anchor=(1, 1), loc=2, fontsize='x-small')
        for legline, origlines in zip(legend.get_texts(), lines):
            togglable_legend.add(legline, origlines)
        row_id += 1

    plt.subplots_adjust(left=0.05, right=0.82, top=0.95, bottom=0.1)
    plt.show()
