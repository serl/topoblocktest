import lib.collection as collection
from collections import OrderedDict


class iperf3m_chain_ns_iptables_fixed_udp(collection.Collection):
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
        'iptables_type': 'stateful',
    }
    variables = OrderedDict([
        ('chain_len', (2, 3, 5, 11)),

        ('parallelism', (1, 4, 6, 8)),
        ('iptables_rules_len', (10, 25, 50, 100, 250, 500, 1000)),
    ])

    def generation_skip_fn(self, settings):
        return (settings['chain_len'] - 1) * settings['iptables_rules_len'] not in (100, 1000)

    x_axis = 'chain_len'
    x_limits = (1.5, 11.5)
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'number of namespaces'

    def analysis_row_key_fn(self, r):
        return "{:>3}{:>6}".format(r['parallelism'], (r['chain_len'] - 1) * r['iptables_rules_len'])

    def analysis_row_label_fn(self, r):
        return "{parallelism} UDP flows, {} total {iptables_type} rules {}".format(', no offloading' if r['disable_offloading'] else '', (r['chain_len'] - 1) * r['iptables_rules_len'], **r)

    def analysis_grouping_fn(self, r):
        return ((r['chain_len'] - 1) * r['iptables_rules_len'],)

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
    iperf3m_chain_ns_iptables_fixed_udp().parse_shell_arguments()
