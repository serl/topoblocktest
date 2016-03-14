import sys, itertools
import lib.topologies as topologies
import lib.tests as tests
from datetime import datetime, timedelta

def test(n_ns, use_ovs, ovs_ns_links, parallelism=1, repetitions=1, mss='default', disable_offloading=False, tcpdump=False):
    settings = {
        'n_ns': int(n_ns),
        'use_ovs': use_ovs,
        'ovs_ns_links': ovs_ns_links,
        'repetitions': repetitions,
        'parallelism': parallelism,
        'mss': mss,
        'disable_offloading': disable_offloading,
        'tcpdump': tcpdump,
        'ns1': 'x-ns1',
    }

    settings['result_file'] = 'results/chain_ns_iperf/'
    if settings['disable_offloading']:
        settings['result_file'] += 'disable_offloading/'
    else:
        settings['result_file'] += 'enable_offloading/'
    settings['result_file'] += '{}/'.format(settings['mss'])
    if settings['use_ovs']:
        settings['result_file'] += 'chain-{parallelism}-{n_ns}-ovs-{ovs_ns_links}'.format(**settings)
    else:
        settings['result_file'] += 'chain-{parallelism}-{n_ns}-direct-veth'.format(**settings)

    m = topologies.ns_chain(settings['n_ns'], settings['use_ovs'], settings['ovs_ns_links'], settings['disable_offloading'])

    script = tests.begin()
    script += m.get_script()
    script += tests.iperf(**settings)

    script.run()

if __name__ == '__main__':
    settings = None
    try:
        settings = {
            'n_ns': int(sys.argv[1]),
            'use_ovs': bool(sys.argv[2]),
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
        for (n_ns, use_ovs, ovs_ns_links, parallelism, mss, disable_offloading) in itertools.product((2, 3, 5, 10, 20), (False, True), ('port', 'veth'), (1, 2, 3, 4, 8, 12), ('default', 536), (True, False)):
            if use_ovs is True and ovs_ns_links == 'port':
                continue
            if (mss is not None or disable_offloading) and parallelism != 4:
                continue
            cases.append((n_ns, use_ovs, ovs_ns_links, parallelism, mss, disable_offloading))

        print('{} experiments to do. Expected end: {}\n'.format(len(cases), datetime.now() + timedelta(seconds=len(cases)*2 + len(cases)*repetitions*35)))
        for (n_ns, use_ovs, ovs_ns_links, parallelism, mss, disable_offloading) in cases:
            test(n_ns, use_ovs, ovs_ns_links, parallelism, repetitions, mss, disable_offloading)
