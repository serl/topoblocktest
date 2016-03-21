import re, pathlib, itertools
from .math_utils import mean_confidence
from collections import OrderedDict

def iperf(results_path):
    #definitions
    class ChainResult:
        def __repr__(self):
            return repr(self.__dict__)
    def get_possibilities(collection, key):
        if isinstance(collection, dict):
            collection = collection.values()
        if len(collection) is 0:
            return []
        return sorted(list(set([getattr(o, key) for l in collection for o in l])))
    re_filename = re.compile(r'^chain-(\d+)-(\d+)-([^\.]+)\.throughput$')

    #logic
    results = {} # chain_len => [ChainResult]
    p = pathlib.Path(results_path)
    for f in p.glob('*/*/*'):
        match = re_filename.search(f.name)
        if match is None:
            continue
        r = ChainResult()
        r.parallelism = int(match.group(1))
        r.chain_len = int(match.group(2))
        r.links_description = match.group(3)
        r.offloading = (f.parts[-3] == 'enable_offloading')
        r.mss = f.parts[-2]
        with f.open() as file_handler:
            values = [int(line.rstrip()) for line in file_handler]
            r.throughput = mean_confidence(values)
            r.len_values = len(values)
        with f.parent.joinpath(f.stem + '.cpu').open() as file_handler:
            values_list = [[], [], [], [], [], []]
            len_values_check = 0
            skip_line = False
            for line in file_handler:
                if skip_line or line.startswith('avg-cpu:'):
                    skip_line = not skip_line # if there's avg-cpu, we skip two lines
                    len_values_check += 0.5 # as we do it twice
                    continue
                row = map(float, line.split())
                for i, v in enumerate(row):
                    values_list[i].append(v)
            # %user %nice %system %iowait %steal %idle
            r.cpu = tuple([mean_confidence(values) for values in values_list])
            if float(r.len_values) != len_values_check:
                raise ValueError('number of values not consistent between throughput and cpu usage')
        if r.chain_len not in results:
            results[r.chain_len] = []
        results[r.chain_len].append(r)

    columns = sorted(results.keys())
    rows = OrderedDict() # label of the serie => [ChainResult]
    for (offloading, mss, parallelism, links_description) in itertools.product(reversed(get_possibilities(results, 'offloading')), reversed(get_possibilities(results, 'mss')), get_possibilities(results, 'parallelism'), get_possibilities(results, 'links_description')):
        label = '{} {} ({}offloading, mss: {})'.format(links_description, parallelism, '' if offloading else 'no ', mss)
        row = []
        for chain_len in columns:
            try:
                subset = [r for r in results[chain_len] if r.offloading == offloading and r.mss == mss and r.parallelism == parallelism and r.links_description == links_description]
                if len(subset) > 1:
                    raise ValueError("Too many values for the constraint.")
                row.append(subset[0])
            except:
                row.append(None)
        if tuple(set(row)) == (None,):
            continue
        rows[label] = row

    return columns, rows
