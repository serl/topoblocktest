import lib.collection as collection
from collections import OrderedDict


class iperf_veth_tests_udp(collection.Collection):
    constants = {
        'protocol': 'udp',
        'topology': 'direct_veth',
        'zerocopy': False,
    }
    variables = OrderedDict([
        ('parallelism', (1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16)),

        ('iperf_name', ('iperf2', 'iperf3', 'iperf3m')),
        ('disable_offloading', (False, True)),
        ('packet_size', (65507, 1458, 36)),
        ('affinity', (False, True)),
    ])

    def generation_skip_fn(self, settings):
        if settings['iperf_name'] == 'iperf2' and (settings['zerocopy'] or settings['affinity']):
            return True
        return False

    x_axis = 'parallelism'
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'parallelism'

    filters = {
        'iperf3m': lambda r: r['iperf_name'] != 'iperf3m',
        'smallpackets': lambda r: r['packet_size'] > 36,
    }

    def analysis_row_label_fn(self, r):
        zcpyaff_label_list = []
        for name in ('zerocopy', 'affinity'):
            if r[name]:
                zcpyaff_label_list.append(name)
        return "{iperf_name} {}offloading, pkt: {packet_size} {}".format('no ' if r['disable_offloading'] else '', ', '.join(zcpyaff_label_list), **r)

    def analysis_grouping_fn(self, r):
        iperf_names = ['iperf2', 'iperf3', 'iperf3m']
        return (iperf_names.index(r['iperf_name']),)

    def plot_style_fn(self, r, group_id):
        color = 'black'
        if r['affinity']:
            color = 'red'
        if r['zerocopy']:
            color = 'blue'
        if r['affinity'] and r['zerocopy']:
            color = 'green'

        marker = '^'
        if r['packet_size'] == 65507:
            marker = 's'
        elif r['packet_size'] == 1458:
            marker = 'o'
        elif r['packet_size'] == 36:
            marker = 'v'

        return {
            'linestyle': '--' if r['disable_offloading'] else '-',
            'color': color,
            'marker': marker,
        }


if __name__ == '__main__':
    iperf_veth_tests_udp().parse_shell_arguments()
