import lib.collection as collection
from collections import OrderedDict


class iperf3m_chain_ns_iptables_udp(collection.Collection):
    constants = {
        'iperf_name': 'iperf3m',
        'protocol': 'udp',
        'topology': 'ns_chain_iptables',
        'disable_offloading': False,
        'zerocopy': False,
        'affinity': False,
        'use_ovs': False,
        'ovs_ns_links': 'veth',
        'packet_size': 32739,
    }
    variables = OrderedDict([
        ('chain_len', (2, 3, 5, 10)),

        ('parallelism', (1, 4, 6, 8)),
        ('iptables_rules_len', (0, 10, 100)),
        ('iptables_type', ('stateless', 'stateful')),
    ])

    x_axis = 'chain_len'
    x_limits = (1.5, 10.5)
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'number of namespaces'

    filters = {
        'paper_10': lambda r: r['iptables_type'] != 'stateful' or r['iptables_rules_len'] != 10,
        'paper_100': lambda r: r['iptables_type'] != 'stateful' or r['iptables_rules_len'] != 100,
    }

    def analysis_row_label_fn(self, r):
        return "{parallelism} UDP flows, {iptables_rules_len} {iptables_type} rules {}".format(', no offloading' if r['disable_offloading'] else '', **r)

    def analysis_grouping_fn(self, r):
        return (r['iptables_rules_len'],)

    def plot_style_fn(self, r, group_id):
        colors = {
            1: 'black',
            4: 'green',
            6: 'red',
            8: 'orange',
        }
        return {
            'linestyle': '--' if r['iptables_type'] == 'stateless' else '-',
            'color': colors[r['parallelism']],
        }


if __name__ == '__main__':
    iperf3m_chain_ns_iptables_udp().parse_shell_arguments()
