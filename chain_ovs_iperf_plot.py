import re, itertools
from pathlib import Path
from lib.math_utils import mean_confidence
from collections import OrderedDict
import matplotlib
matplotlib.use('qt4agg')
import matplotlib.pyplot as plt
from lib.plot import TogglableLegend

class ChainResult:
    def __repr__(self):
        return repr(self.__dict__)

def get_possibilities(collection, key):
    if isinstance(collection, dict):
        collection = collection.values()
    if len(collection) is 0:
        return []
    return sorted(list(set([getattr(o, key) for l in collection for o in l])))

re_filename = re.compile(r'^chain-(\d+)-(\d+)-([^-_]+)-([^-_\.]+)\.throughput$')
results = {} # n_ovs => [ChainResult]
results_path = 'results/chain_ovs_iperf/'
p = Path(results_path)
for f in p.glob('*/*/*'):
    match = re_filename.search(f.name)
    if match is None:
        continue
    r = ChainResult()
    r.parallelism = int(match.group(1))
    r.n_ovs = int(match.group(2))
    r.ovs_ovs_links = match.group(3)
    r.ovs_ns_links = match.group(4)
    r.offloading = (f.parts[-3] == 'enable_offloading')
    r.mss = f.parts[-2]
    with f.open() as file_handler:
        values = [int(line.rstrip()) for line in file_handler]
        r.throughput = mean_confidence(values)
    with f.parent.joinpath(f.stem + '.cpu').open() as file_handler:
        sums = [0.0]*6
        length = 0
        skip_line = False
        for line in file_handler:
            if skip_line or line.startswith('avg-cpu:'):
                skip_line = not skip_line # if there's avg-cpu, we skip two lines
                continue
            row = map(float, line.split())
            for i, v in enumerate(row):
                sums[i] += v
            length += 1
        # %user %nice %system %iowait %steal %idle
        r.cpu = tuple([v/length for v in sums]) #TODO: add confidence intervals!
    if r.n_ovs not in results:
        results[r.n_ovs] = []
    results[r.n_ovs].append(r)

columns = sorted(results.keys())
rows_number = 3
rows = []
styles = []
colors = {
    ('patch', 'port'): 'red',
    ('patch', 'veth'): 'blue',
    ('veth', 'port'): 'green',
    ('veth', 'veth'): 'black',
}
for i in range(rows_number):
    rows.append(OrderedDict()) # label of the serie => [ChainResult]
    styles.append({}) # label of the serie => **kwargs for matplotlib
for (offloading, mss, parallelism, ovs_ovs_links, ovs_ns_links) in itertools.product(reversed(get_possibilities(results, 'offloading')), get_possibilities(results, 'mss'), get_possibilities(results, 'parallelism'), get_possibilities(results, 'ovs_ovs_links'), get_possibilities(results, 'ovs_ns_links')):
    links_type = (ovs_ovs_links, ovs_ns_links)
    label = '{} {} ({}offloading, mss: {})'.format('-'.join(links_type), parallelism, '' if offloading else 'no ', mss)
    row = []
    for n_ovs in columns:
        try:
            subset = [r for r in results[n_ovs] if r.offloading == offloading and r.mss == mss and r.parallelism == parallelism and (r.ovs_ovs_links, r.ovs_ns_links) == links_type]
            if len(subset) > 1:
                raise ValueError("Too many values for the constraint.")
            row.append(subset[0])
        except:
            row.append(None)
    if tuple(set(row)) == (None,):
        continue
    basestyle = { 'color': colors[links_type], 'linestyle': '-', 'markersize': 7 }
    if offloading and mss == 'default':
        if parallelism <= 4:
            row_id = 0
            rows[row_id][label] = row
            styles[row_id][label] = basestyle.copy()
            if parallelism is 1:
                styles[row_id][label]['marker'] = 'o'
            elif parallelism is 2:
                styles[row_id][label]['marker'] = '^'
            elif parallelism is 4:
                styles[row_id][label]['marker'] = 's'
        if parallelism >= 4:
            row_id = 1
            rows[row_id][label] = row
            styles[row_id][label] = basestyle.copy()
            if parallelism is 4:
                styles[row_id][label]['marker'] = 's'
            elif parallelism is 8:
                styles[row_id][label]['marker'] = '^'
            elif parallelism is 12:
                styles[row_id][label]['marker'] = 'o'
    if parallelism == 4:
        row_id = 2
        rows[row_id][label] = row
        styles[row_id][label] = basestyle.copy()
        if mss == 'default':
            styles[row_id][label]['marker'] = '^'
        else:
            styles[row_id][label]['marker'] = 'o'
        if not offloading:
            styles[row_id][label]['linestyle'] = '--'

fig, axes = plt.subplots(rows_number, 2, sharex=True)
togglable_legend = TogglableLegend(fig)
for row_id, (ax_throughput, ax_cpu) in enumerate(axes):
    lines = []
    for label, row in rows[row_id].items():
        x_values = []
        throughput_values = []
        throughput_error = []
        cpu_values = []
        for i, col in enumerate(columns):
            try:
                r = row[i]
                throughput_values.append(r.throughput[0])
                throughput_error.append(r.throughput[1])
                cpu_values.append(100-r.cpu[5]) # 100-idle
                x_values.append(col)
            except:
                pass
        kwargs = styles[row_id][label] if label in styles[row_id] else {}
        series_lines = []
        line, two, three = ax_throughput.errorbar(x_values, throughput_values, yerr=throughput_error, label=label, **kwargs)
        series_lines.extend((line,) + two + three)
        series_lines += ax_cpu.plot(x_values, cpu_values, label=label, **kwargs)
        lines.append(series_lines)
    ax_throughput.set_xlabel('number of bridges')
    ax_throughput.set_ylabel('throughput (b/s)')
    ax_throughput.grid(True)
    ax_cpu.set_xlabel('number of bridges')
    ax_cpu.set_ylabel('cpu utilization (%)')
    ax_cpu.grid(True)
    ax_cpu.axis([None, None, 10, 105])

    legend = ax_cpu.legend(bbox_to_anchor=(1, 1), loc=2, fontsize='x-small')
    for legline, origlines in zip(legend.get_lines(), lines):
        togglable_legend.add(legline, origlines)

plt.subplots_adjust(left=0.05, right=0.82, top=0.95, bottom=0.1)
plt.show()
