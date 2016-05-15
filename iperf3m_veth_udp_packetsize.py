import lib.collection as collection
from collections import OrderedDict


class iperf3m_veth_udp_packetsize(collection.Collection):
    constants = {
        'protocol': 'udp',
        'iperf_name': 'iperf3m',
        'topology': 'direct_veth',
        'zerocopy': False,
    }
    variables = OrderedDict([
        ('packet_size', tuple([2048 * (m + 1) - 29 for m in range(0, 32)])),

        ('disable_offloading', (False, True)),
        ('affinity', (False, True)),
        ('parallelism', (1, 3, 4, 5, 6, 8, 12, 24)),
    ])

    def generation_skip_fn(self, settings):
        return settings['affinity'] and settings['disable_offloading']

    x_axis = 'packet_size'
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'packet size (B)'

    filters = {
        'paper': lambda r: r['affinity'] or r['disable_offloading'] or r['parallelism'] not in (1, 4, 6, 8),
    }

    def analysis_row_label_fn(self, r):
        return "{parallelism} UDP flows{}{}".format(', no offloading' if r['disable_offloading'] else '', ', affinity' if r['affinity'] else '', **r)

    def analysis_grouping_fn(self, r):
        return (r['affinity'] + 2 * r['disable_offloading'],)

    def plot_style_fn(self, r, group_id):
        colors = {
            1: 'black',
            3: 'blue',
            4: 'green',
            5: 'purple',
            6: 'red',
            8: 'orange',
            12: 'cyan',
            24: 'yellow',
        }
        linestyle = '-'
        if r['disable_offloading']:
            linestyle = '--'
        elif r['affinity']:
            linestyle = ':'
        return {
            'linestyle': linestyle,
            'color': colors[r['parallelism']],
        }


if __name__ == '__main__':
    iperf3m_veth_udp_packetsize().parse_shell_arguments()
