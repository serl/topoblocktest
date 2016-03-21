from lib import plot
from lib import analyze
import sys

def usage():
    print('usage: python {} <ovs|ns> [csv|plot]'.format(*sys.argv))
    sys.exit(1)

if len(sys.argv) < 2:
    usage()

chain_type = sys.argv[1]
if chain_type not in ('ovs', 'ns'):
    usage()

action = 'csv'
try:
    action = sys.argv[2]
except IndexError:
    pass
if action not in ('csv', 'plot'):
    usage()

cols, rows = analyze.iperf('results/chain_{}_iperf/'.format(chain_type))


if action == 'csv':
    data_header = 'label,'+',,'.join(map(str, cols))+','
    throughput_values = ''
    cpu_values = ''
    for label, values in rows.items():
        throughput_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v.throughput)) if v is not None else ',' for v in values]))
        cpu_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v.cpu[5])) if v is not None else ',' for v in values]))
    print('throughput')
    print(data_header)
    print(throughput_values)
    print('cpu idle')
    print(data_header)
    print(cpu_values)
elif action == 'plot':
    if chain_type == 'ovs':
        colors = {
            'patch-port': 'red',
            'patch-veth': 'blue',
            'veth-port': 'green',
            'veth-veth': 'black',
        }
        x_title = 'number of bridges'
    elif chain_type == 'ns':
        colors = {
            'direct-veth': 'purple',
            'ovs-port': 'green',
            'ovs-veth': 'black',
        }
        x_title = 'number of namespaces'
    plot.iperf(columns=cols, rows=rows, x_title=x_title, colors=colors)
