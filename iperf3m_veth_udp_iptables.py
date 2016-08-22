import lib.collection as collection
from collections import OrderedDict
import math


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
        ('iptables_rules_len', (0, 10, 100, 500, 1000, 5000)),

        ('parallelism', (1, 4, 6, 8)),
        ('iptables_type', ('stateless', 'stateful')),
    ])

    x_axis = 'iptables_rules_len'
    x_limits = (-50, 5050)
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'number of iptables rules'

    filters = {
        'paper': lambda r: r['iptables_rules_len'] > 1000,
    }

    def analysis_row_label_fn(self, r):
        return "{parallelism} UDP flows, {iptables_type} rules {}".format(', no offloading' if r['disable_offloading'] else '', **r)

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

    def plot_hook(self, ax, row_id, y_ax, x_values, y_values, y_error, style):
        # trick everything else so to have a nice fake scale
        new_x_values = [math.sqrt(val) for i, val in enumerate(x_values)]
        max_new_x_values = max(new_x_values)
        self.x_limits = (-max_new_x_values * .03, max_new_x_values * 1.03)
        ax.set_xticks(new_x_values)
        ax.set_xticklabels(x_values)
        for i, value in enumerate(x_values):  # must do like this, as x_value must retain its reference
            x_values[i] = new_x_values[i]
        return True


if __name__ == '__main__':
    iperf3m_veth_udp_iptables().parse_shell_arguments()
