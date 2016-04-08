import lib.test_master as test_master


if __name__ == '__main__':
    constants = {
        'protocol': 'tcp',
        'topology': 'ns_chain',
        'ovs_ns_links': 'port',
        'packet_size': 'default',
    }
    variables = {
        'iperf_name': ('iperf', 'iperf3', 'iperf3m'),
        'parallelism': (1, 2, 3, 4, 8, 12, 16),
        'disable_offloading': (False, True),
        'chain_len': (2, 3, 5, 10),
        'use_ovs': (False, True),
        'zerocopy': (False, True),
        'affinity': (False, True),
    }

    def skip_fn(settings):
        if (settings['packet_size'] != 'default' or settings['disable_offloading']) and settings['parallelism'] != 4:
            return True
        if settings['iperf_name'] == 'iperf':
            if settings['zerocopy'] or settings['affinity']:
                return True
            else:
                #reuse already done tests (by generate_iperf_chain_ns.py), as if these two keys are present, a different hash will result
                settings.pop('zerocopy')
                settings.pop('affinity')

    test_master.generate_combinations(constants, variables, skip_fn)
