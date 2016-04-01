import sys, itertools
import lib.topologies as topologies
import lib.tests as tests
from datetime import datetime, timedelta

def test(parallelism=1, repetitions=1, mss='default', disable_offloading=False, tcpdump=False):
    settings = {
        'repetitions': repetitions,
        'parallelism': parallelism,
        'mss': mss,
        'disable_offloading': disable_offloading,
        'tcpdump': tcpdump,
    }

    settings['result_file'] = 'results/veth_iperf/'
    if settings['disable_offloading']:
        settings['result_file'] += 'disable_offloading/'
    else:
        settings['result_file'] += 'enable_offloading/'
    settings['result_file'] += '{mss}/chain-{parallelism}-0-veth'.format(**settings)

    m, ns1, ns2 = topologies.direct_veth(settings['disable_offloading'])
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
            'parallelism': int(sys.argv[1]),
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
        for (parallelism, mss, disable_offloading) in itertools.product((1, 2, 3, 4, 8, 12, 16), ('default', 536), (True, False)):
            if (mss != 'default' or disable_offloading) and parallelism != 4:
                continue
            cases.append((parallelism, mss, disable_offloading))

        print('{} experiments to do. Expected end: {}\n'.format(len(cases), datetime.now() + timedelta(seconds=len(cases)*2 + len(cases)*repetitions*35)))
        for (parallelism, mss, disable_offloading) in cases:
            test(parallelism, repetitions, mss, disable_offloading)
