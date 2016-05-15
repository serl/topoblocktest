import lib.collection as collection
from collections import OrderedDict


class iperf3m_chain_ovs_tcp(collection.Collection):
    constants = {
        'iperf_name': 'iperf3m',
        'protocol': 'tcp',
        'packet_size': 'default',
        'topology': 'ovs_chain',
        'affinity': False,
    }
    variables = OrderedDict([
        ('chain_len', (1, 2, 3, 5, 10, 20)),

        ('disable_offloading', (False, True)),
        ('parallelism', (1, 4, 6, 8, 12)),
        ('zerocopy', (False, True)),
        ('ovs_ovs_links', ('patch', 'veth')),
        ('ovs_ns_links', ('port', 'veth')),
    ])

    def generation_skip_fn(self, settings):
        if settings['disable_offloading'] and settings['parallelism'] != 4:
            return True

    x_axis = 'chain_len'
    x_limits = (0, 21)
    y_axes = ['throughput', 'cpu']
    x_title = 'number of OvS switches'

    filters = {
        'no-veth': lambda r: r['ovs_ns_links'] == 'veth',
        'paper': lambda r: r['disable_offloading'] or r['parallelism'] != 8 or (r['ovs_ns_links'] == 'port' and r['ovs_ovs_links'] == 'veth') or (r['ovs_ns_links'] == 'veth' and r['ovs_ovs_links'] == 'patch'),
    }

    def get_link_label(self, r):
        return '{ovs_ovs_links}-{ovs_ns_links}'.format(**r)

    def analysis_row_label_fn(self, r):
        return "{parallelism} flows over {}{}{}".format(self.get_link_label(r), ', zerocopy' if r['zerocopy'] else '', ', no offloading' if r['disable_offloading'] else '', **r)

    def analysis_grouping_fn(self, r):
        groups = []
        if not r['disable_offloading']:
            groups.append(0)
        if r['parallelism'] == 4:
            groups.append(1)
        return groups

    def plot_style_fn(self, r, group_id):
        colors = {
            'patch-port': 'red',
            'patch-veth': 'blue',
            'veth-port': 'green',
            'veth-veth': 'black',
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

        linestyle = '-'
        if r['disable_offloading']:
            linestyle = ':'
        elif r['zerocopy']:
            linestyle = '--'

        return {
            'color': colors[self.get_link_label(r)],
            'linestyle': linestyle,
            # 'marker': marker,
        }


if __name__ == '__main__':
    iperf3m_chain_ovs_tcp().parse_shell_arguments()
