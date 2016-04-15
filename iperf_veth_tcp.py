import lib.collection as collection


class iperf_veth_tests(collection.Collection):
    constants = {
        'protocol': 'tcp',
        'topology': 'direct_veth',
    }
    variables = {
        'iperf_name': ('iperf2', 'iperf3', 'iperf3m'),
        'parallelism': (1, 2, 3, 4, 8, 12, 16),
        'packet_size': ('default', 536),
        'disable_offloading': (False, True),
        'zerocopy': (False, True),
        'affinity': (False, True),
    }

    def generation_skip_fn(self, settings):
        if settings['iperf_name'] == 'iperf2' and (settings['zerocopy'] or settings['affinity']):
            return True
        return False

    x_axis = 'parallelism'
    x_title = 'parallelism'

    def analysis_row_key_fn(self, r):
        zcpyaff_key = '{}{}'.format('z' if r['zerocopy'] else 'a', 'z' if r['affinity'] else 'a')
        return "{iperf_name: <7}-{}-{:05d}-{}".format('z' if r['disable_offloading'] else 'a', r['packet_size'] if r['packet_size'] != 'default' else 0, zcpyaff_key, **r)
        # TODO: move it into superclass, and substitute with row_key_attributes

    def analysis_row_label_fn(self, r):
        zcpyaff_label_list = []
        for name in ('zerocopy', 'affinity'):
            if r[name]:
                zcpyaff_label_list.append(name)
        return "{iperf_name} {}offloading, pkt: {packet_size} {}".format('no ' if r['disable_offloading'] else '', ', '.join(zcpyaff_label_list), **r)

    def analysis_grouping_fn(self, r):
        iperf_names = ['iperf2', 'iperf3', 'iperf3m']
        return (iperf_names.index(r['iperf_name']),)

    def plot_style_fn(self, r, group_id):
        color = 'black'
        if r['affinity']:
            color = 'red'
        if r['zerocopy']:
            color = 'blue'
        if r['affinity'] and r['zerocopy']:
            color = 'green'

        if r['packet_size'] == 'default':
            marker = 's'
        elif r['packet_size'] == 536:
            marker = '^'

        return {
            'linestyle': '--' if r['disable_offloading'] else '-',
            'color': color,
            'marker': marker,
        }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('action', choices=('generate', 'csv', 'plot'), help='action to take')
    args = parser.parse_args()
    coll = iperf_veth_tests()
    getattr(coll, args.action)()