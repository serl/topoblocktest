import re, math, itertools
import numpy as np
from scipy.stats import t
from pathlib import Path

def mean_confidence(data, confidence=.95):
    values = np.array(data)
    mean = values.mean()
    #confidence_interval = t.interval(confidence, values.size-1, loc=mean, scale=values.std()/math.sqrt(values.size))
    h = values.std() / math.sqrt(values.size) * t.ppf((1+confidence)/2., values.size-1)
    return (mean, h)

re_filename = re.compile(r'^chain-(\d+)-(\d+)-([^-_]+)-([^-_]+)$')
files = []
results_path = 'results/chain_ovs_iperf/'
p = Path(results_path)
for f in p.iterdir():
    match = re_filename.search(f.name)
    if match is None:
        continue
    files.append(match.groups())

columns = sorted(list(set([int(f[1]) for f in files])))
parallelisms = sorted(list(set([int(f[0]) for f in files])))
link_type_pairs = sorted(list(set([(f[2], f[3]) for f in files])))
#header
output = 'link-type,parallelism,' + ',,'.join(map(str, columns)) + '\n'
#lines
for (parallelism, link_type_pair_tuple) in itertools.product(parallelisms, link_type_pairs):
    link_pair = '-'.join(link_type_pair_tuple)
    csv_line = '{},{},'.format(link_pair, parallelism)
    means_conf = []
    for n in columns:
        try:
            with open('{}/chain-{}-{}-{}'.format(results_path, parallelism, n, link_pair)) as file_handler:
                values = [int(line.rstrip()) for line in file_handler]
                means_conf.extend(mean_confidence(values))
        except FileNotFoundError:
            means_conf.extend(('',''))
    csv_line += ','.join(map(str, means_conf))
    output += csv_line + '\n'

with open(results_path + '/chain-summary.csv', 'w') as f:
    f.write(output)
