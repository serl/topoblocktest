#!/usr/bin/env python

import argparse
import argcomplete
import re
from collections import OrderedDict
import lib.topologies as topologies
from lib.test_master import generate

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--run', type=int, default=0, help='immediately run the test N times (a negative value will make the test run abs(N) times, dropping you to bash before the cleanup)', metavar='N')
    type_group = parser.add_argument_group('test type')
    type_group.add_argument('--iperf_name', default='iperf3m', choices=('iperf2', 'iperf3', 'iperf3m'), help='choses the iperf version')
    type_group.add_argument('--parallelism', type=int, default=1, help='number parallel flows')
    type_group.add_argument('--protocol', default='tcp', choices=('tcp', 'udp'), help='Protocol to test')
    type_group.add_argument('--packet_size', default='default', help='Packet size for UDP or Maximum Segment Size for TCP (MTU - 40 bytes)')
    type_group.add_argument('--zerocopy', action='store_true', help='pass the --zerocopy option to iperf3')
    type_group.add_argument('--affinity', action='store_true', help='set automatically the --affinity option on iperf3')

    topo_group = parser.add_argument_group('topology')
    topologies_infos = OrderedDict()
    for obj_name in dir(topologies):
        obj = getattr(topologies, obj_name)
        if not callable(obj) or 'arguments' not in dir(obj):
            continue
        topologies_infos[obj_name] = obj.arguments
    topologies_names = sorted(list(topologies_infos.keys()), key=len)
    topo_group.add_argument('--topology', default=topologies_names[0], choices=topologies_names, help='define topology type')
    topo_group.add_argument('--disable_offloading', default=False, action='store_true', help='disable offloading (jumbo packets)')
    for topo_name in topologies_names:
        topo_arguments = topologies_infos[topo_name]
        arg_group = parser.add_argument_group('{} specific options'.format(topo_name))
        for arg_name, arg_args in topo_arguments.items():
            arg_group.add_argument('--{}_{}'.format(topo_name, arg_name), **arg_args)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    settings = vars(args)  # this is not a copy!
    run = settings.pop('run', False)
    for topo_name in reversed(topologies_names):
        keep = (topo_name == settings['topology'])
        for arg_name in tuple(settings.keys()):
            if arg_name.startswith(topo_name):
                if keep:
                    new_name = re.sub('^{}_'.format(topo_name), '', arg_name)
                    settings[new_name] = settings.pop(arg_name)
                else:
                    settings.pop(arg_name)
    test_hash, script = generate(**settings)
    for x in range(abs(run)):
        script.run(run < 0)
    print('Test hash: {}'.format(test_hash))
