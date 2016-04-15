from lib import plot
from lib import analyze
from lib.test_master import get_results_db
import sys


def run_analysis(collection, action):
    db = get_results_db()
    # defaults
    x_title = ''
    x_axis = ''
    db_query = db
    get_link_label = lambda r: 'unknown'
    row_info_fn = None
    grouping_fn = None

    def style_fn(r, group_id):
        colors = {
            'patch-port': 'red',
            'patch-veth': 'blue',
            'veth-port': 'green',
            'veth-veth': 'black',
            'direct-veth': 'purple',
            'ovs-port': 'green',
            'ovs-veth': 'black',
        }
        if r['parallelism'] == 1:
            marker = 's'
        elif r['parallelism'] == 2:
            marker = '^'
        elif r['parallelism'] == 3:
            marker = 'v'
        elif r['parallelism'] == 4:
            marker = 'o'
            if r['packet_size'] != 'default':
                marker = '^'
        elif r['parallelism'] == 8:
            marker = 's'
        elif r['parallelism'] == 12:
            marker = '^'
        elif r['parallelism'] == 16:
            marker = 'v'
        return {
            'color': colors[get_link_label(r)],
            'linestyle': '--' if r['disable_offloading'] else '-',
            'marker': marker,
        }

    if collection == 'veth':
        x_title = 'parallelism'
        x_axis = 'parallelism'  # key on result dict
        db_query = [r for r in db if r['topology'] == 'direct_veth']

        def row_info_fn(r):
            zcpyaff_key = 'aa'
            zcpyaff_label = ''
            if r['iperf_name'] != 'iperf2':
                zcpyaff_key = '{}{}'.format('z' if r['zerocopy'] else 'a', 'z' if r['affinity'] else 'a')
                zcpyaff_label_list = []
                for name in ('zerocopy', 'affinity'):
                    if r[name]:
                        zcpyaff_label_list.append(name)
                zcpyaff_label = ', '.join(zcpyaff_label_list)
            key = "{iperf_name: <7}-{}-{:05d}-{}".format('z' if r['disable_offloading'] else 'a', r['packet_size'] if r['packet_size'] != 'default' else 0, zcpyaff_key, **r)
            label = "{iperf_name} {}offloading, pkt: {packet_size} {}".format('no ' if r['disable_offloading'] else '', zcpyaff_label, **r)
            return key, label

        def grouping_fn(r):
            iperf_names = ['iperf2', 'iperf3', 'iperf3m']
            return (iperf_names.index(r['iperf_name']),)
        style_fn = lambda r, group_id: {'linestyle': '--' if r['disable_offloading'] else '-', }

    elif collection == 'ovs':
        x_title = 'number of bridges'
        x_axis = 'chain_len'  # key on result dict
        db_query = [r for r in db if r['topology'] == 'ovs_chain' and r['iperf_name'] == 'iperf2']

        def row_info_fn(r):
            key = "{}-{:05d}-{parallelism:05d}-{ovs_ovs_links}-{ovs_ns_links}".format('z' if r['disable_offloading'] else 'a', r['packet_size'] if r['packet_size'] != 'default' else 0, **r)
            label = "{ovs_ovs_links}-{ovs_ns_links} {parallelism} ({}offloading, pkt: {packet_size})".format('no ' if r['disable_offloading'] else '', **r)
            return key, label

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

        get_link_label = lambda r: "{ovs_ovs_links}-{ovs_ns_links}".format(**r)

    elif collection == 'ns':
        x_title = 'number of namespaces'
        x_axis = 'chain_len'  # key on result dict
        db_query = [r for r in db if r['topology'] == 'ns_chain' and r['iperf_name'] == 'iperf2']

        def get_link_label(r):
            link_label = 'direct-veth'
            if r['use_ovs']:
                link_label = 'ovs-{ovs_ns_links}'.format(**r)
            return link_label

        def row_info_fn(r):
            key = "{}-{:05d}-{parallelism:05d}-{}-{ovs_ns_links}".format('z' if r['disable_offloading'] else 'a', r['packet_size'] if r['packet_size'] != 'default' else 0, 'a' if r['use_ovs'] else 'z', **r)
            label = "{} {parallelism} ({}offloading, pkt: {packet_size})".format(get_link_label(r), 'no ' if r['disable_offloading'] else '', **r)
            return key, label

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

    elif collection == 'iperf_cmp':
        x_title = 'number of namespaces'
        x_axis = 'chain_len'  # key on result dict
        db_query = [r for r in db if
                    r['topology'] == 'ns_chain' and
                    r['chain_len'] in (2, 3, 5, 10) and
                    r['ovs_ns_links'] == 'port' and
                    r['packet_size'] == 'default'
                    ]

        def get_link_label(r):
            link_label = 'direct-veth'
            if r['use_ovs']:
                link_label = 'ovs-{ovs_ns_links}'.format(**r)
            return link_label

        def row_info_fn(r):
            key = "{iperf_name: <7}-{}-{parallelism:05d}-{}-{ovs_ns_links}-{}-{}".format('z' if r['disable_offloading'] else 'a', 'a' if r['use_ovs'] else 'z', 'z' if r['zerocopy'] else 'a', 'z' if r['affinity'] else 'a', **r)
            label = "{iperf_name} {} {parallelism} ({}{}{})".format(get_link_label(r), '' if r['disable_offloading'] else 'offloading', ' zerocopy' if r['zerocopy'] else '', ' affinity' if r['affinity'] else '', **r)
            return key, label

        def grouping_fn(r):
            groups = []
            iperf_names = ['iperf2', 'iperf3', 'iperf3m']
            iperf_plots = 2 if r['iperf_name'] == 'iperf2' else 5
            if not r['disable_offloading'] and r['packet_size'] == 'default' and not r['zerocopy'] and not r['affinity']:
                groups.append(iperf_names.index(r['iperf_name']) * iperf_plots)
            if r['parallelism'] == 4:
                groups.append(iperf_names.index(r['iperf_name']) * iperf_plots + 1)
            if r['zerocopy'] or r['affinity']:
                groups.append(iperf_names.index(r['iperf_name']) * iperf_plots + r['zerocopy'] * 2 + r['affinity'])
            return groups

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
        plot.throughput_cpu(cols, rows_grouped, x_title, style_fn)


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
