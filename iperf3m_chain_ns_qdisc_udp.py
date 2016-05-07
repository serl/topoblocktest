import lib.collection as collection
from collections import OrderedDict
import re


class iperf3m_chain_ns_qdisc_udp(collection.Collection):
    constants = {
        'iperf_name': 'iperf3m',
        'protocol': 'udp',
        'disable_offloading': False,
        'zerocopy': False,
        'affinity': False,
        'packet_size': 32739,
        'use_ovs': False,
        'ovs_ns_links': 'veth',
    }
    variables = OrderedDict([
        ('chain_len', (2, 3, 5, 10)),

        ('topology', ('ns_chain', 'ns_chain_qdisc_netem', 'ns_chain_qdisc_htb')),
        ('parallelism', (1, 4, 6, 8, 12)),
    ])

    def generation_skip_fn(self, settings):
        if not settings['use_ovs'] and settings['ovs_ns_links'] == 'port':
            return True

    x_axis = 'chain_len'
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'number of namespaces'

    def get_link_label(self, r):
        link_label = 'direct-veth'
        if r['use_ovs']:
            link_label = 'ovs-{ovs_ns_links}'.format(**r)
        return link_label

    def analysis_row_label_fn(self, r):
        qdisc_label = ''
        if r['topology'].startswith('ns_chain_qdisc_'):
            qdisc_label = re.sub('^ns_chain_qdisc_', '', r['topology'])
        return "{} {parallelism} {} (pkt: {packet_size})".format(self.get_link_label(r), qdisc_label, **r)

    def analysis_grouping_fn(self, r):
        topo_names = ['ns_chain', 'ns_chain_qdisc_netem', 'ns_chain_qdisc_htb']
        return (topo_names.index(r['topology']),)

    def plot_style_fn(self, r, group_id):
        colors = {
            'direct-veth': 'purple',
            'ovs-port': 'green',
            'ovs-veth': 'black',
        }
        if r['parallelism'] == 1:
            marker = 's'
        elif r['parallelism'] == 4:
            marker = '^'
        elif r['parallelism'] == 6:
            marker = 'v'
        elif r['parallelism'] == 8:
            marker = 'o'
        elif r['parallelism'] == 12:
            marker = '.'
        return {
            'color': colors[self.get_link_label(r)],
            'linestyle': '--' if r['disable_offloading'] else '-',
            'marker': marker,
        }


if __name__ == '__main__':
    iperf3m_chain_ns_qdisc_udp().parse_shell_arguments()
