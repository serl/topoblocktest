import sys, itertools
import lib.topologies as topologies
import lib.tests as tests
from datetime import datetime, timedelta

def test(n_ovs, ovs_ovs_links, ovs_ns_links, parallelism=1, repetitions=1, mss='default', disable_offloading=False, tcpdump=False):
    settings = {
        'n_ovs': int(n_ovs),
        'ovs_ovs_links': ovs_ovs_links,
        'ovs_ns_links': ovs_ns_links,
        'repetitions': repetitions,
        'parallelism': parallelism,
        'mss': mss,
        'disable_offloading': disable_offloading,
        'tcpdump': tcpdump,
    }

    settings['result_file'] = 'results/chain_ovs_iperf/'
    if settings['disable_offloading']:
        settings['result_file'] += 'disable_offloading/'
    else:
        settings['result_file'] += 'enable_offloading/'
    settings['result_file'] += '{}/'.format(settings['mss'])
    settings['result_file'] += 'chain-{parallelism}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}'.format(**settings)

    m, ns1, ns2 = topologies.ovs_chain(settings['n_ovs'], settings['ovs_ovs_links'], settings['ovs_ns_links'], settings['disable_offloading'])
    settings['ns1'] = ns1
    settings['ns2'] = ns2

    script = tests.begin()
    script += m.get_script()
    script += tests.iperf(**settings)

    script.run()

if __name__ == '__main__':
    settings = None
    try:
        settings = {
            'n_ovs': int(sys.argv[1]),
            'ovs_ovs_links': sys.argv[2],
            'ovs_ns_links': sys.argv[3],
            'parallelism': int(sys.argv[4]),
        }
    except (IndexError, ValueError):
        pass
    if settings is not None:
        #run the requested test
        test(**settings)
    else:
        #run the complete set!
        repetitions = 10
        cases = []
        for (n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, mss, disable_offloading) in itertools.product((0, 1, 2, 3, 5, 10, 20, 30, 50), ('patch', 'veth'), ('port', 'veth'), (1, 2, 4, 8, 12), ('default', 536), (True, False)):
            if n_ovs is 0 and (ovs_ovs_links != 'veth' or ovs_ns_links != 'veth'):
                continue
            if (mss is not None or disable_offloading) and parallelism != 4:
                continue
            cases.append((n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, mss, disable_offloading))

        print('{} experiments to do. Expected end: {}\n'.format(len(cases), datetime.now() + timedelta(seconds=len(cases)*2 + len(cases)*repetitions*35)))
        for (n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, mss, disable_offloading) in cases:
            test(n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, repetitions, mss, disable_offloading)
