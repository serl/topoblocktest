from lib import plot
from lib import analyze
from lib.test_master import get_results_db
import sys


def run_analysis(collection, action):
    db = get_results_db(True)
    grouping_fn=lambda row_element: (0,)

    if collection == 'veth':
        x_title = 'parallelism'
        x_axis = 'parallelism'  # key on result dict
        db_query = [r for r in db if r['topology'] == 'direct_veth' and r['iperf_name'] == 'iperf2']

        def row_info_fn(r):
            key = "{}-{:05d}".format('z' if r['disable_offloading'] else 'a', r['packet_size'] if r['packet_size'] != 'default' else 0)
            label = "{}offloading, pkt: {packet_size}".format('no ' if r['disable_offloading'] else '', **r)
            color = None
            return key, label, color

    elif collection == 'ovs':
        x_title = 'number of bridges'
        x_axis = 'chain_len'  # key on result dict
        db_query = [r for r in db if r['topology'] == 'ovs_chain' and r['iperf_name'] == 'iperf2']

        def row_info_fn(r):
            key = "{}-{:05d}-{parallelism:05d}-{ovs_ovs_links}-{ovs_ns_links}".format('z' if r['disable_offloading'] else 'a', r['packet_size'] if r['packet_size'] != 'default' else 0, **r)
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
    elif collection == 'ns':
        colors = {
            'direct-veth': 'purple',
            'ovs-port': 'green',
            'ovs-veth': 'black',
        }
        x_title = 'number of namespaces'
        db_query = [r for r in db if r['topology'] == 'ns_chain' and r['iperf_name'] == 'iperf2']
    elif collection == 'iperf_cmp':
        x_title = 'number of namespaces'
        x_axis = 'chain_len'  # key on result dict

    cols, rows, rows_grouped = analyze.get_analysis_table(db_query, x_axis, row_info_fn, grouping_fn)

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
    print('usage: python {} <veth|ovs|ns|iperf_cmp> [csv|plot]'.format(*sys.argv))
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()

    collection = sys.argv[1]
    if collection not in ('veth', 'ovs', 'ns', 'iperf_cmp'):
        usage()

    action = 'csv'
    try:
        action = sys.argv[2]
    except IndexError:
        pass
    if action not in ('csv', 'plot'):
        usage()

    run_analysis(collection, action)
