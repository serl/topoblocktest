import lib.test_master as test_master


if __name__ == '__main__':
    constants = {
        'iperf_name': 'iperf2',
        'protocol': 'tcp',
        'topology': 'direct_veth',
    }
    variables = {
        'parallelism': (1, 2, 3, 4, 8, 12, 16),
        'packet_size': ('default', 536),
        'disable_offloading': (False, True),
    }

    test_master.generate_combinations(constants, variables)
