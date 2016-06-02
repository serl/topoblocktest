import lib.collection as collection
from collections import OrderedDict


class iperf3m_chain_ns_udp(collection.Collection):
    constants = {
        'iperf_name': 'iperf3m',
        'protocol': 'udp',
        'topology': 'ns_chain',
        'disable_offloading': False,
        'zerocopy': False,
        'affinity': False,
    }
    variables = OrderedDict([
        ('chain_len', (2, 3, 5, 10, 20)),

        ('parallelism', (1, 4, 6, 8, 12)),
        ('packet_size', (65507, 32739, 36)),
        ('use_ovs', (False, True)),
        ('ovs_ns_links', ('port', 'veth')),
    ])

    def generation_skip_fn(self, settings):
        if not settings['use_ovs'] and settings['ovs_ns_links'] == 'port':
            return True

    x_axis = 'chain_len'
    x_limits = (1, 21)
    y_axes = ['throughput', 'packetput', 'cpu']
    x_title = 'number of namespaces'

    filters = {
        'rightsize': lambda r: r['packet_size'] != 32739,
        'paper-8': lambda r: r['packet_size'] != 32739 or r['parallelism'] != 8 or (r['use_ovs'] and r['ovs_ns_links'] == 'veth'),
        'paper-6': lambda r: r['packet_size'] != 32739 or r['parallelism'] != 6 or (r['use_ovs'] and r['ovs_ns_links'] == 'veth'),
        'paper-8_veth': lambda r: r['packet_size'] != 32739 or r['parallelism'] != 8 or r['use_ovs'],
        'paper-parallelism': lambda r: r['packet_size'] != 32739 or r['parallelism'] > 8 or (r['use_ovs'] and r['ovs_ns_links'] == 'veth'),
    }

    def get_link_label(self, r):
        link_label = 'veth'
        if r['use_ovs']:
            link_label = 'ovs-{ovs_ns_links}'.format(**r)
        return link_label

    def analysis_row_label_fn(self, r):
        link_label = self.get_link_label(r)
        if link_label == 'ovs-port':
            link_label = 'OvS'
        return "{parallelism} UDP flows over {}".format(link_label, **r)

    def analysis_grouping_fn(self, r):
        return (r['packet_size'],)

    def plot_style_fn(self, r, group_id):
        if self.is_filter_selected('paper-6') or self.is_filter_selected('paper-8') or self.is_filter_selected('paper-8_veth'):
            colors = {
                'veth': 'red',
                'ovs-port': 'black',
                'ovs-veth': 'gray',
            }
            return {
                'color': colors[self.get_link_label(r)],
            }
        colors = {
            1: 'black',
            4: 'green',
            6: 'red',
            8: 'orange',
            12: 'blue',
        }
        linestyles = {
            'veth': '-',
            'ovs-port': '--',
            'ovs-veth': ':',
        }
        marker = ''
        if r['packet_size'] == 65507:
            marker = 's'
        elif r['packet_size'] == 36:
            marker = '^'
        return {
            'color': colors[r['parallelism']],
            'linestyle': linestyles[self.get_link_label(r)],
            'marker': marker,
        }


if __name__ == '__main__':
    iperf3m_chain_ns_udp().parse_shell_arguments()
