import sys, itertools
import lib.topologies as topologies
import lib.tests as tests
from datetime import datetime, timedelta

def test(**settings):
    settings['result_file'] = 'results/chain_ns_iperf_compare/'
    if settings['disable_offloading']:
        settings['result_file'] += 'disable_offloading/'
    else:
        settings['result_file'] += 'enable_offloading/'
    settings['result_file'] += '{}/'.format(settings['mss'])
    settings['__iperf_options_signature'] = ''
    if settings['affinity']:
        settings['__iperf_options_signature'] += 'aff'
    if settings['zerocopy']:
        settings['__iperf_options_signature'] += 'zcp'
    if settings['use_ovs']:
        settings['result_file'] += 'chain-{parallelism}-{n_ns}-{iperf_name}{__iperf_options_signature}-ovs-{ovs_ns_links}'.format(**settings)
    else:
        settings['result_file'] += 'chain-{parallelism}-{n_ns}-{iperf_name}{__iperf_options_signature}-direct-veth'.format(**settings)

    m, ns1, ns2 = topologies.ns_chain(settings['n_ns'], settings['use_ovs'], settings['ovs_ns_links'], settings['disable_offloading'])
    settings['ns1'] = ns1
    settings['ns2'] = ns2

    script = tests.begin()
    script += m.get_script()
    script += getattr(tests, settings['iperf_name'])(**settings)

    script.run()

if __name__ == '__main__':
    from optparse import OptionParser
    if len(sys.argv) > 1:
        parser = OptionParser()
        iperf_flavours = ('iperf', 'iperf3', 'iperf3m')
        parser.add_option('--iperf_name', dest='iperf_name', default='iperf', type='choice', choices=iperf_flavours, help='choses the iperf version: {} [default: %default]'.format(iperf_flavours))
        parser.add_option('--parallelism', dest='parallelism', type='int', default=1, help='number parallel flows [default: %default]')
        parser.add_option('--n_ns', dest='n_ns', type='int', default=2, help='number of namespaces to chain [default: %default]')
        parser.add_option('--use_ovs', dest='use_ovs', default=False, action='store_true', help='use OvS switches to link the namespaces')
        link_types = ('port', 'veth')
        parser.add_option('--ovs_ns_links', dest='ovs_ns_links', default='port', type='choice', choices=link_types, help='choses the link type between OvS and namespaces, if OvS is enabled: {} [default: %default]'.format(link_types))
        parser.add_option('--mss', dest='mss', default='default', help='Maximum Segment Size [default: 1460]')
        parser.add_option('--disable_offloading', dest='disable_offloading', default=False, action='store_true', help='disable offloading (jumbo packets)')
        (options, args) = parser.parse_args()
        #run the requested test
        test(**options.__dict__)
    else:
        #run the complete set!
        repetitions = 10
        cases = []
        for iperf_name in ('iperf', 'iperf3', 'iperf3m'):
            for (n_ns, use_ovs, ovs_ns_links, parallelism, mss, disable_offloading, zerocopy, affinity) in itertools.product((2, 3, 5, 10), (False, True), ('port', ), (1, 2, 4, 8, 12, 16), ('default', ), (True, False), (True, False), (True, False)):
                if not use_ovs and ovs_ns_links == 'port':
                    continue
                if (zerocopy or affinity) and iperf_name == 'iperf':
                    continue
                if (mss != 'default' or disable_offloading) and parallelism != 4:
                    continue
                cases.append({
                    'iperf_name': iperf_name,
                    'n_ns': n_ns,
                    'use_ovs': use_ovs,
                    'ovs_ns_links': ovs_ns_links,
                    'parallelism': parallelism,
                    'mss': mss,
                    'disable_offloading': disable_offloading,
                    'zerocopy': zerocopy,
                    'affinity': affinity,
                })

        print('{} experiments to do. Expected end: {}\n'.format(len(cases), datetime.now() + timedelta(seconds=len(cases)*2 + len(cases)*repetitions*35)))
        for settings in cases:
            test(**settings)
