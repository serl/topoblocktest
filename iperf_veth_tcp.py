import lib.collection as collection
from collections import OrderedDict


class iperf_veth_tcp(collection.Collection):
    constants = {
        'protocol': 'tcp',
        'topology': 'direct_veth',
    }
    variables = OrderedDict([
        ('parallelism', (1, 2, 3, 4, 5, 6, 7, 8, 12, 16)),

        ('iperf_name', ('iperf2', 'iperf3', 'iperf3m')),
        ('disable_offloading', (False, True)),
        ('packet_size', ('default', 536)),
        ('zerocopy', (False, True)),
        ('affinity', (False, True)),
    ])

    def generation_skip_fn(self, settings):
        if settings['iperf_name'] == 'iperf2' and (settings['zerocopy'] or settings['affinity']):
            return True
        return False

    x_axis = 'parallelism'
    y_axes = ['throughput', 'cpu']
    x_title = 'parallelism'

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

        if r['packet_size'] == 'default':
            marker = 's'
        elif r['packet_size'] == 536:
            marker = '^'

        return {
            'linestyle': '--' if r['disable_offloading'] else '-',
            'color': color,
            'marker': marker,
        }


if __name__ == '__main__':
    iperf_veth_tcp().parse_shell_arguments()
