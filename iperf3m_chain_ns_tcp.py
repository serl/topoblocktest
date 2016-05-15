import lib.collection as collection
from collections import OrderedDict


class iperf3m_chain_ns_tcp(collection.Collection):
    constants = {
        'iperf_name': 'iperf3m',
        'protocol': 'tcp',
        'packet_size': 'default',
        'topology': 'ns_chain',
        'disable_offloading': False,
        'affinity': False,
    }
    variables = OrderedDict([
        ('chain_len', (2, 3, 5, 10, 20)),

        ('parallelism', (1, 4, 6, 8, 12)),
        ('zerocopy', (False, True)),
        ('use_ovs', (False, True)),
        ('ovs_ns_links', ('port', 'veth')),
    ])

    def generation_skip_fn(self, settings):
        if not settings['use_ovs'] and settings['ovs_ns_links'] == 'port':
            return True

    x_axis = 'chain_len'
    x_limits = (1, 21)
    y_axes = ['throughput', 'cpu']
    x_title = 'number of namespaces'

    filters = {
        'paper': lambda r: r['parallelism'] != 8 or (r['use_ovs'] and r['ovs_ns_links'] == 'veth'),
    }

    def get_link_label(self, r):
        link_label = 'veth'
        if r['use_ovs']:
            link_label = 'ovs-{ovs_ns_links}'.format(**r)
        return link_label

    def analysis_row_label_fn(self, r):
        zerocopy_label = ', zerocopy' if r['zerocopy'] else ''
        link_label = self.get_link_label(r)
        if link_label == 'ovs-port':
            link_label = 'OvS'
        return "{parallelism} TCP flows over {}{}".format(link_label, zerocopy_label, **r)

    def analysis_grouping_fn(self, r):
        return (r['parallelism'],)

    def plot_style_fn(self, r, group_id):
        colors = {
            'veth': 'red',
            'ovs-port': 'black',
            'ovs-veth': 'gray',
        }
        return {
            'color': colors[self.get_link_label(r)],
            'linestyle': '--' if r['zerocopy'] else '-',
        }


if __name__ == '__main__':
    iperf3m_chain_ns_tcp().parse_shell_arguments()
