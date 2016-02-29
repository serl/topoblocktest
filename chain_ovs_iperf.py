import sys, itertools
import lib.topologies as topologies
from lib.bash import CommandBlock

def test(n_ovs, ovs_ovs_links, ovs_ns_links, repetitions=1):
    settings = {
        'id': 'chain',
        'n_ovs': int(n_ovs),
        'ovs_ovs_links': ovs_ovs_links,
        'ovs_ns_links': ovs_ns_links,
    }

    m = topologies.ovs_chain(settings['n_ovs'], settings['ovs_ovs_links'], settings['ovs_ns_links'])

    script = CommandBlock()
    script += '#!/bin/bash'
    script += m.get_script()
    script += ''

    #topology check
    topology = CommandBlock()
    topology += 'ovs-vsctl show > results/{id}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}_topology'
    topology += 'echo -e "\\nip a on x-ns1" >> results/{id}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}_topology'
    topology += 'ip netns exec x-ns1 ip a >> results/{id}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}_topology'
    topology += 'echo -e "\\nip a on x-ns2" >> results/{id}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}_topology'
    topology += 'ip netns exec x-ns2 ip a >> results/{id}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}_topology'
    script += topology.format(**settings)

    settings['repetitions'] = repetitions
    for mss in ((1460),): #536
        #settings['mss'] = mss

        script += """
        ip netns exec x-ns1 iperf -s &>/dev/null & IPERF_PID=$!
        for i in `seq {repetitions}`; do
            echo -n "Running iperf ($i)... "
            sleep 1
            csvline=$(ip netns exec x-ns2 iperf -c 10.113.1.1 -y C)
            measure=${{csvline##*,}}
            echo measured $(numfmt --to=iec --suffix=b/s $measure)
            echo $measure >> results/{id}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}
        done
        kill $IPERF_PID && sleep 1
        """.format(**settings) #--mss {mss} seems not to work :/

    script.run()

if __name__ == '__main__':
    settings = None
    try:
        settings = {
            'n_ovs': int(sys.argv[1]),
            'ovs_ovs_links': sys.argv[2],
            'ovs_ns_links': sys.argv[3],
        }
    except (IndexError, ValueError):
        pass
    if settings is not None:
        #run the requested test
        test(**settings)
    else:
        #run the complete set!
        for (n_ovs, ovs_ovs_links, ovs_ns_links) in itertools.product((0, 1, 2, 3, 5, 10, 20, 30, 50, 99), ('patch', 'veth'), ('port', 'veth')):
            print(n_ovs, ovs_ovs_links, ovs_ns_links, 10)
