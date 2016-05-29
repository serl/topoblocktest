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

        ('topology', ('ns_chain', 'ns_chain_qdisc_netem', 'ns_chain_qdisc_htb', 'ns_chain_qdisc_netem_tera', 'ns_chain_qdisc_htb_tera')),
        ('parallelism', (1, 4, 6, 8, 12)),
    ])

    def generation_skip_fn(self, settings):
        if not settings['use_ovs'] and settings['ovs_ns_links'] == 'port':
            return True

    x_axis = 'chain_len'
    x_limits = (1.5, 10.5)
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'number of namespaces'

    filters = {
        'paper': lambda r: r['topology'] != 'ns_chain_qdisc_htb_tera' or r['parallelism'] > 8,
    }

    def get_link_label(self, r):
        link_label = 'direct-veth'
        if r['use_ovs']:
            link_label = 'ovs-{ovs_ns_links}'.format(**r)
        return link_label

    def analysis_row_label_fn(self, r):
        qdisc_label = 'pfifo_fast'
        if r['topology'].startswith('ns_chain_qdisc_'):
            qdisc_label = re.sub('^ns_chain_qdisc_', '', r['topology']).replace('_', ' ')
        return "{parallelism} UDP flows, {}{}".format(qdisc_label, ', no offloading' if r['disable_offloading'] else '', **r)

    def analysis_grouping_fn(self, r):
        topo_names = list(self.variables['topology'])
        return (topo_names.index(r['topology']),)

    def plot_style_fn(self, r, group_id):
        colors = {
            1: 'black',
            4: 'green',
            6: 'red',
            8: 'orange',
            12: 'blue',
        }
        return {
            'linestyle': '--' if r['iptables_type'] == 'stateless' else '-',
            'color': colors[r['parallelism']],
        }


if __name__ == '__main__':
    iperf3m_chain_ns_qdisc_udp().parse_shell_arguments()
