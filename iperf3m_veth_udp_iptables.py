import lib.collection as collection
from collections import OrderedDict


class iperf3m_veth_udp_iptables(collection.Collection):
    constants = {
        'iperf_name': 'iperf3m',
        'protocol': 'udp',
        'topology': 'ns_chain_iptables',
        'disable_offloading': False,
        'zerocopy': False,
        'affinity': False,
        'use_ovs': False,
        'ovs_ns_links': 'veth',
        'chain_len': 2,
        'packet_size': 32739,
    }
    variables = OrderedDict([
        ('iptables_rules_len', (0, 10, 100, 500, 1000)),

        ('parallelism', (1, 4, 6, 8)),
        ('iptables_type', ('stateless', 'stateful')),
    ])

    x_axis = 'iptables_rules_len'
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'number of rules'

    def analysis_row_label_fn(self, r):
        return "{iperf_name} ({parallelism} flows, {}offloading) {protocol} {iptables_type} rules.".format('no ' if r['disable_offloading'] else '', **r)

    def plot_style_fn(self, r, group_id):
        colors = {
            1: 'black',
            4: 'green',
            6: 'blue',
            8: 'orange',
        }
        return {
            'linestyle': '--' if r['iptables_type'] == 'stateless' else '-',
            'color': colors[r['parallelism']],
        }


if __name__ == '__main__':
    iperf3m_veth_udp_iptables().parse_shell_arguments()
