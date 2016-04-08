import lib.test_master as test_master


if __name__ == '__main__':
    constants = {
        'iperf_name': 'iperf',
        'protocol': 'tcp',
        'topology': 'ovs_chain',
    }
    variables = {
        'parallelism': (1, 2, 3, 4, 8, 12, 16),
        'packet_size': ('default', 536),
        'disable_offloading': (False, True),
        'chain_len': (1, 2, 3, 5, 10, 20, 30, 50),
        'ovs_ovs_links': ('patch', 'veth'),
        'ovs_ns_links': ('port', 'veth'),
    }

    def skip_fn(settings):
        if (settings['packet_size'] != 'default' or settings['disable_offloading']) and settings['parallelism'] != 4:
            return True

    test_master.generate_combinations(constants, variables, skip_fn)
