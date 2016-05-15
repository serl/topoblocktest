import lib.collection as collection
from collections import OrderedDict


class iperf_veth_tcp(collection.Collection):
    constants = {
        'protocol': 'tcp',
        'topology': 'direct_veth',
    }
    variables = OrderedDict([
        ('parallelism', (1, 2, 3, 4, 5, 6, 7, 8, 12, 16)),

        ('iperf_name', ('iperf2', 'iperf3', 'iperf3m')),
        ('disable_offloading', (False, True)),
        ('packet_size', ('default', 536)),
        ('zerocopy', (False, True)),
        ('affinity', (False, True)),
    ])

    def generation_skip_fn(self, settings):
        if settings['iperf_name'] == 'iperf2' and (settings['zerocopy'] or settings['affinity']):
            return True
        return False

    x_axis = 'parallelism'
    x_limits = (0, 17)
    y_axes = ['throughput', 'cpu']
    x_title = '# of parallel flows'

    filters = {
        'iperf3m': lambda r: r['iperf_name'] != 'iperf3m',
        'rightsize': lambda r: r['packet_size'] != 'default',
        'paper': lambda r: r['iperf_name'] != 'iperf3m' or r['packet_size'] != 'default' or r['affinity'] or r['disable_offloading'],
    }

    def analysis_row_label_fn(self, r):
        zcpyaff_label_list = []
        for name in ('zerocopy', 'affinity'):
            if r[name]:
                zcpyaff_label_list.append(name)
        zcpyaff_label = ', '.join(zcpyaff_label_list)
        label_parts = []
        if r['iperf_name'] != 'iperf3m':
            label_parts.append(r['iperf_name'])
        label_parts.append('TCP over veth')
        if r['disable_offloading']:
            label_parts.append('no offloading')
        if r['packet_size'] != 'default':
            label_parts.append('pktsize: {}'.format(r['packet_size']))
        if len(zcpyaff_label):
            label_parts.append(zcpyaff_label)
        return ', '.join(label_parts)

    def analysis_grouping_fn(self, r):
        iperf_names = list(self.variables['iperf_name'])
        packet_sizes = list(self.variables['packet_size'])
        return (iperf_names.index(r['iperf_name']) * len(packet_sizes) + packet_sizes.index(r['packet_size']),)

    def plot_style_fn(self, r, group_id):
        linestyle = '-'
        if r['affinity']:
            linestyle = ':'
        if r['zerocopy']:
            linestyle = '--'
        if r['affinity'] and r['zerocopy']:
            linestyle = '-.'

        return {
            'linestyle': linestyle,
            'color': 'red' if r['disable_offloading'] else 'black',
        }


if __name__ == '__main__':
    iperf_veth_tcp().parse_shell_arguments()
