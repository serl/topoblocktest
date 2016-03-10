import re, itertools
from pathlib import Path
from lib.math_utils import mean_confidence
from collections import OrderedDict
import matplotlib
matplotlib.use('qt4agg')
import matplotlib.pyplot as plt

class ChainResult:
    def __repr__(self):
        return repr(self.__dict__)

def get_possibilities(collection, key):
    if isinstance(collection, dict):
        collection = collection.values()
    if len(collection) is 0:
        return []
    return sorted(list(set([getattr(o, key) for l in collection for o in l])))

re_filename = re.compile(r'^chain-(\d+)-(\d+)-([^-_]+)-([^-_]+)$')
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
    if r.n_ovs not in results:
        results[r.n_ovs] = []
    results[r.n_ovs].append(r)

columns = sorted(results.keys())
rows_ids = ('offloading', '4')
rows = {}
styles = {}
colors = {
    ('patch', 'port'): 'red',
    ('patch', 'veth'): 'blue',
    ('veth', 'port'): 'green',
    ('veth', 'veth'): 'black',
}
for id in rows_ids:
    rows[id] = OrderedDict() # label of the serie => [ChainResult]
    styles[id] = {} # label of the serie => **kwargs for matplotlib
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
    basestyle = { 'color': colors[links_type], 'linestyle': '-' }
    if offloading and mss == 'default':
        rows['offloading'][label] = row
        styles['offloading'][label] = basestyle.copy()
        if parallelism is 1:
            styles['offloading'][label]['marker'] = 'o'
        elif parallelism is 2:
            styles['offloading'][label]['marker'] = '^'
        elif parallelism is 4:
            styles['offloading'][label]['marker'] = 's'
        elif parallelism is 8:
            styles['offloading'][label]['marker'] = '+'
        elif parallelism is 12:
            styles['offloading'][label]['marker'] = 'x'
    if parallelism == 4:
        rows['4'][label] = row
        styles['4'][label] = basestyle.copy()
        if mss == 'default':
            styles['4'][label]['marker'] = '+'
        else:
            styles['4'][label]['marker'] = 'x'
        if not offloading:
            styles['4'][label]['linestyle'] = '--'

fig, axes = plt.subplots(2, 1)
ax = {}
ax['offloading'], ax['4'] = axes

for id in ('offloading', '4'):
    for label, row in rows[id].items():
        cur_x = []
        cur_y = []
        cur_yerr=[]
        for i, col in enumerate(columns):
            try:
                r = row[i]
                cur_y.append(r.throughput[0])
                cur_yerr.append(r.throughput[1])
                cur_x.append(col)
            except:
                pass
        kwargs = {}
        if label in styles[id]:
            kwargs = styles[id][label]
        ax[id].errorbar(cur_x, cur_y, yerr=cur_yerr, label=label, **kwargs)
    ax[id].set_xlabel('number of bridges')
    ax[id].set_ylabel('throughput')
    ax[id].legend(bbox_to_anchor=(1, 1), loc=2, fontsize='x-small')

plt.subplots_adjust(left=0.05, right=0.82, top=0.95, bottom=0.1)
plt.show()
