from . import analyze
#imports are inside functions!!!1

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

def iperf(results_path=None, columns=None, rows=None, x_title='', colors={}):
    #import
    from collections import OrderedDict
    plt = import_matplotlib()

    if columns is None and rows is None:
        columns, rows = analyze.iperf(results_path)

    rows_number = 3
    rows_grouped = []
    styles = []
    for i in range(rows_number):
        rows_grouped.append(OrderedDict()) # label of the serie => [ChainResult]
        styles.append({}) # label of the serie => **kwargs for matplotlib
    for label, row in rows.items():
        first_value = [c for c in row if c is not None][0]
        basestyle = { 'linestyle': '-', 'markersize': 7 }
        if first_value.links_description in colors:
            basestyle['color'] = colors[first_value.links_description]
        if first_value.offloading and first_value.mss == 'default':
            if first_value.parallelism <= 4:
                row_id = 0
                rows_grouped[row_id][label] = row
                styles[row_id][label] = basestyle.copy()
                if first_value.parallelism is 1:
                    styles[row_id][label]['marker'] = 'o'
                elif first_value.parallelism is 2:
                    styles[row_id][label]['marker'] = '^'
                elif first_value.parallelism is 3:
                    styles[row_id][label]['marker'] = 'v'
                elif first_value.parallelism is 4:
                    styles[row_id][label]['marker'] = 's'
            if first_value.parallelism >= 4:
                row_id = 1
                rows_grouped[row_id][label] = row
                styles[row_id][label] = basestyle.copy()
                if first_value.parallelism is 4:
                    styles[row_id][label]['marker'] = 's'
                elif first_value.parallelism is 8:
                    styles[row_id][label]['marker'] = 'o'
                elif first_value.parallelism is 12:
                    styles[row_id][label]['marker'] = '^'
                elif first_value.parallelism is 16:
                    styles[row_id][label]['marker'] = 'v'
        if first_value.parallelism == 4:
            row_id = 2
            rows_grouped[row_id][label] = row
            styles[row_id][label] = basestyle.copy()
            if first_value.mss == 'default':
                styles[row_id][label]['marker'] = '^'
            else:
                styles[row_id][label]['marker'] = 'o'
            if not first_value.offloading:
                styles[row_id][label]['linestyle'] = '--'

    fig, axes = plt.subplots(rows_number, 2, sharex=True)
    togglable_legend = TogglableLegend(fig)
    for row_id, (ax_throughput, ax_cpu) in enumerate(axes):
        lines = []
        for label, row in rows_grouped[row_id].items():
            x_values = []
            throughput_values = []
            throughput_error = []
            cpu_values = []
            cpu_error = []
            for i, col in enumerate(columns):
                try:
                    r = row[i]
                    throughput_values.append(r.throughput[0])
                    throughput_error.append(r.throughput[1])
                    cpu_values.append(100-r.cpu[5][0]) # 100-idle
                    cpu_error.append(r.cpu[5][1])
                    x_values.append(col)
                except AttributeError:
                    pass
            kwargs = styles[row_id][label] if label in styles[row_id] else {}
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

    plt.subplots_adjust(left=0.05, right=0.82, top=0.95, bottom=0.1)
    plt.show()
