import lib.collection as collection
from collections import OrderedDict


class iperf3m_veth_udp_packetsize(collection.Collection):
    constants = {
        'protocol': 'udp',
        'iperf_name': 'iperf3m',
        'topology': 'direct_veth',
        'zerocopy': False,
        'affinity': False,
    }
    variables = OrderedDict([
        ('packet_size', tuple([2048 * (m + 1) - 29 for m in range(0, 32)])),

        ('disable_offloading', (False, True)),
        ('parallelism', (1, 3, 6, 8, 12, 24)),
    ])

    x_axis = 'packet_size'
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'packet size (B)'

    def analysis_row_label_fn(self, r):
        return "{iperf_name} ({parallelism} flows, {}offloading) {protocol}".format('no ' if r['disable_offloading'] else '', **r)

    def plot_style_fn(self, r, group_id):
        colors = {
            1: 'black',
            3: 'blue',
            6: 'green',
            8: 'purple',
            12: 'red',
            24: 'yellow',
        }
        return {
            'linestyle': '--' if r['disable_offloading'] else '-',
            'color': colors[r['parallelism']],
        }


if __name__ == '__main__':
    iperf3m_veth_udp_packetsize().parse_shell_arguments()
