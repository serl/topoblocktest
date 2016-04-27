import lib.collection as collection
from collections import OrderedDict


class iperf3m_veth_udp_packetsize(collection.Collection):
    constants = {
        'protocol': 'udp',
        'iperf_name': 'iperf3m',
        'parallelism': 6,
        'topology': 'direct_veth',
        'zerocopy': False,
        'affinity': False,
        'disable_offloading': False,
    }
    variables = OrderedDict([
        ('packet_size', tuple([2048 * (m + 1) - 29 for m in range(0, 32)])),
    ])

    x_axis = 'packet_size'
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'packet size (B)'

    def analysis_row_label_fn(self, r):
        return "{iperf_name} ({parallelism} flows) {protocol}".format(**r)


if __name__ == '__main__':
    iperf3m_veth_udp_packetsize().parse_shell_arguments()
