from lib import plot
from lib import analyze
from lib.test_master import get_results_db
import sys


def analyze_chain(chain_type, action):
    db = get_results_db(True)

    if chain_type == 'ovs':
        x_title = 'number of bridges'
        db_query = [r for r in db if r['topology'] == 'ovs_chain' and r['iperf_name'] == 'iperf2']

        def row_info_fn(r):
            key = ''
            key += 'z' if r['disable_offloading'] else 'a'
            key += '{:05d}'.format(r['packet_size']) if r['packet_size'] != 'default' else '00000'
            key += "{parallelism:05d}-{ovs_ovs_links}-{ovs_ns_links}".format(**r)
            label = "{ovs_ovs_links}-{ovs_ns_links} {parallelism} ({}offloading, pkt: {packet_size})".format('no ' if r['disable_offloading'] else '', **r)
            colors = {
                'patch-port': 'red',
                'patch-veth': 'blue',
                'veth-port': 'green',
                'veth-veth': 'black',
            }
            color = colors["{ovs_ovs_links}-{ovs_ns_links}".format(**r)]
            return key, label, color

        def grouping_fn(r):
            groups = []
            if not r['disable_offloading'] and r['packet_size'] == 'default':
                if r['parallelism'] <= 4:
                    groups.append(0)
                if r['parallelism'] >= 4:
                    groups.append(1)
            if r['parallelism'] == 4:
                groups.append(2)
            return groups
    elif chain_type == 'ns':
        colors = {
            'direct-veth': 'purple',
            'ovs-port': 'green',
            'ovs-veth': 'black',
        }
        x_title = 'number of namespaces'
        db_query = [r for r in db if r['topology'] == 'ns_chain' and r['iperf_name'] == 'iperf2']
    elif chain_type == 'iperf_cmp':
        x_title = 'number of namespaces'

    cols, rows, rows_grouped = analyze.get_chain_analysis(db_query, row_info_fn, grouping_fn)

    if action == 'csv':
        data_header = 'label,' + ',,'.join(map(str, cols)) + ','
        throughput_values = ''
        cpu_values = ''
        fairness_values = ''
        for label, rowdetails in rows.items():
            values = rowdetails['row']
            throughput_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v['iperf_result']['throughput'])) if v is not None else ',' for v in values]))
            cpu_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v['iostat_cpu']['idle'])) if v is not None else ',' for v in values]))
            fairness_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v['iperf_result']['fairness'] if 'fairness' in v['iperf_result'] else '')) if v is not None else ',' for v in values]))
        print('throughput')
        print(data_header)
        print(throughput_values)
        print('cpu idle')
        print(data_header)
        print(cpu_values)
        print('fairness')
        print(data_header)
        print(fairness_values)
    elif action == 'plot':
        plot.chain(cols, rows_grouped, x_title)


def usage():
    print('usage: python {} <ovs|ns|iperf_cmp> [csv|plot]'.format(*sys.argv))
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()

    chain_type = sys.argv[1]
    if chain_type not in ('ovs', 'ns', 'iperf_cmp'):
        usage()

    action = 'csv'
    try:
        action = sys.argv[2]
    except IndexError:
        pass
    if action not in ('csv', 'plot'):
        usage()

    analyze_chain(chain_type, action)
