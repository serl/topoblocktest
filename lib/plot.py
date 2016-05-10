import matplotlib
import matplotlib.ticker
import warnings
# the other imports are inside functions!!!1


def import_matplotlib_pyplot(interactive=True):
    if interactive:
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
    decimal_positions = 1 if max(div_values) < 10 else 0
    return map("{{:.{}f}}".format(decimal_positions).format, div_values), power


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

    def __set_visibility(self, legline, visibility=None):
        origlines = self.__lines_legend[legline]
        if visibility == None:
            # toggle
            visibility = not origlines[0].get_visible()
        for origline in origlines:
            origline.set_visible(visibility)
        # Change the alpha on the line in the legend so we can see what lines
        # have been toggled
        if visibility:
            legline.set_alpha(1.0)
        else:
            legline.set_alpha(0.4)

    def __onpick(self, event):
        # on the pick event, find the orig line corresponding to the
        # legend proxy line, and toggle the visibility
        legline = event.artist
        if event.mouseevent.button == 1:
            self.__set_visibility(legline)
        elif event.mouseevent.button == 3:
            for ll in self.__lines_legend.keys():
                visibility = (ll == legline) if not event.mouseevent.dblclick else True
                self.__set_visibility(ll, visibility)
        self.fig.canvas.draw()


class YAx:

    @classmethod
    def get_instance(cls, attr_name, is_relative):
        if attr_name == 'throughput':
            return ThroughputAx(is_relative)
        elif attr_name == 'cpu':
            return CpuAx(is_relative)
        elif attr_name == 'packetput':
            return PacketputAx(is_relative)

    def __init__(self, is_relative):
        self.is_relative = is_relative

    def get_value(self, r):
        raise ValueError('Must be implemented in subclass')

    def format_ax(self, ax):
        pass


class ThroughputAx(YAx):

    def get_value(self, r):
        try:
            return r['iperf_result']['throughput']
        except TypeError:
            return None

    def format_ax(self, ax):
        if self.is_relative:
            ax.set_ylabel('throughput (% gain relative to ref)')
        else:
            ax.yaxis.set_major_formatter(PrefixFormatter())
            ax.set_ylabel('throughput (b/s)')
        ax.grid(True)


class CpuAx(YAx):

    def get_value(self, r):
        try:
            return (100 - r['iostat_cpu']['idle'][0], r['iostat_cpu']['idle'][1])  # 100 - idle
        except TypeError:
            return None

    def format_ax(self, ax):
        if self.is_relative:
            ax.set_ylabel('cpu utilization (% gain relative to ref)')
        else:
            ax.set_ylabel('cpu utilization (%)')
            ax.axis([None, None, 0, 102])
        ax.grid(True)


class PacketputAx(YAx):

    def get_value(self, r):
        try:
            return r['iperf_result']['packetput']
        except TypeError:
            return None

    def format_ax(self, ax):
        if self.is_relative:
            ax.set_ylabel('throughput (% gain relative to ref)')
        else:
            ax.yaxis.set_major_formatter(PrefixFormatter())
            ax.set_ylabel('throughput (pps)')
        ax.grid(True)


class PrefixFormatter(matplotlib.ticker.Formatter):
    __powers = ['', 'K', 'M', 'G', 'T', 'P']
    __divisor = 1000
    __cache = {}

    def __call__(self, x, pos=None):  # pos=None when trying to display the value on the statusbar (you're hovering the plot with the pointer)
        if pos is None:
            return x
        locs_tuple = tuple(self.locs)
        if locs_tuple not in self.__cache:
            div_values = self.locs.copy()
            div_xmax = self.locs[-1]
            power_index = 0
            while div_xmax >= self.__divisor and power_index < len(self.__powers):
                div_values = [x / self.__divisor for x in div_values]
                div_xmax = div_values[-1]
                power_index += 1
            power = self.__powers[power_index]
            decimals = [str(int(n))[-(power_index * 3):] for n in self.locs]
            decimal_lengths = [len(n.replace('0', '')) for n in decimals]
            decimal_positions = max(decimal_lengths)
            self.__cache[locs_tuple] = tuple(map("{{:.{}f}}{}".format(decimal_positions, power).format, div_values))
        return self.__cache[locs_tuple][pos]


def dynamic(collection, export=None):
    columns, rows, rows_grouped = collection.analyze()
    y_axes = collection.y_axes
    window_title = collection.__class__.__name__

    if collection.is_relative():
        window_title += ' relative to: ' + ' '.join(['{}={}'.format(k, v) for k, v in collection.reference.items()])

    if len(rows_grouped) == 0 or len(y_axes) == 0:
        raise ValueError('Nothing to plot')
    for i, y_ax in enumerate(y_axes):
        if isinstance(y_ax, str):
            y_axes[i] = YAx.get_instance(y_ax, collection.is_relative())
    # import
    from collections import OrderedDict
    plt = import_matplotlib_pyplot(interactive=(export is None))

    fig, all_axes = plt.subplots(len(rows_grouped), len(y_axes), sharex=(export is None))
    fig.canvas.set_window_title(window_title)
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
                    # warnings.warn("Missing value on serie '{}' for x value {}".format(label, col_name), RuntimeWarning)
                    continue
                row_element = r
                for y_ax_index, y_ax in enumerate(y_axes):
                    value_error = y_ax.get_value(r)
                    if value_error is None:
                        warnings.warn("Missing value on serie '{}' for y_ax '{}'".format(label, y_ax.__class__.__name__), RuntimeWarning)
                        continue
                    if not isinstance(value_error, tuple):
                        value_error = (value_error, 0)
                    if collection.is_relative():
                        ref_r = collection.get_reference_row(r)
                        if ref_r is None:
                            # warnings.warn("Missing reference value on serie '{}' for x value {}".format(label, col_name), RuntimeWarning)
                            continue
                        ref_value_error = y_ax.get_value(ref_r)
                        if not isinstance(ref_value_error, tuple):
                            ref_value_error = (ref_value_error, 0)
                        plot_values[y_ax_index].append((value_error[0] - ref_value_error[0]) * 100 / ref_value_error[0])
                        plot_errors[y_ax_index].append(0)  # think a way to calculate it
                    else:
                        plot_values[y_ax_index].append(value_error[0])
                        plot_errors[y_ax_index].append(value_error[1])
                    x_values[y_ax_index].append(col_name)

            # draw plot
            basestyle = {'linestyle': '-', 'markersize': 7}
            kwargs = basestyle.copy()
            kwargs.update(collection.plot_style_fn(row_element, row_id))
            series_lines = []
            for y_ax_index, mpl_ax in enumerate(axes_row):
                if not len(x_values[y_ax_index]):
                    continue
                y_ax = y_axes[y_ax_index]
                line, two, three = mpl_ax.errorbar(x_values[y_ax_index], plot_values[y_ax_index], yerr=plot_errors[y_ax_index], label=label, **kwargs)
                series_lines.extend((line,) + two + three)
                mpl_ax.set_xlabel(collection.x_title)
                y_ax.format_ax(mpl_ax)
                if mpl_ax.get_xlim()[1] > 1000:
                    mpl_ax.xaxis.set_major_formatter(PrefixFormatter())
            lines.append(series_lines)

        legend = mpl_ax.legend(bbox_to_anchor=(1, 1), loc=2, fontsize='x-small')
        if legend is not None:  # it may happen, if we have no series on that axis :/
            for legline, origlines in zip(legend.get_texts(), lines):
                togglable_legend.add(legline, origlines)
        row_id += 1

    if export is not None:
        fig.set_size_inches(len(y_axes) * 7.5, len(rows_grouped) * 4)
        fig.savefig(export, bbox_inches='tight')
    else:
        plt.subplots_adjust(left=0.05, right=0.82, top=0.95, bottom=0.1)
        plt.show()
