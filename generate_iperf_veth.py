import lib.test_master as test_master


if __name__ == '__main__':
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

    def skip_fn(settings):
        if settings['iperf_name'] == 'iperf2':
            if settings['zerocopy'] or settings['affinity']:
                return True
            else:
                # they make no sense for iperf2, so they deserve to disappear.
                settings.pop('zerocopy')
                settings.pop('affinity')

    test_master.generate_combinations(constants, variables, skip_fn)
