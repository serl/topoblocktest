import sys, itertools
import lib.topologies as topologies
from lib.bash import CommandBlock

def test(n_ovs, ovs_ovs_links, ovs_ns_links, parallelism=1, repetitions=1):
    settings = {
        'id': 'chain',
        'n_ovs': int(n_ovs),
        'ovs_ovs_links': ovs_ovs_links,
        'ovs_ns_links': ovs_ns_links,
        'repetitions': repetitions,
        'parallelism': parallelism,
    }

    m = topologies.ovs_chain(settings['n_ovs'], settings['ovs_ovs_links'], settings['ovs_ns_links'])

    script = CommandBlock()
    script += '#!/bin/bash'
    script += m.get_script()
    script += ''
    script += 'umask 0000' #as the script will be run as root, this ensures that after you can play around as normal user ;)
    script += 'TEST_DIR="results/chain_ovs_iperf" EXPORT_FILE="$TEST_DIR/{id}-{parallelism}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}"'.format(**settings)
    script += 'mkdir -p "$TEST_DIR"'

    #topology check
    topology = CommandBlock()
    topology += 'ovs-vsctl show > ${{EXPORT_FILE}}_topology'
    topology += 'echo -e "\\nip a on x-ns1" >> ${{EXPORT_FILE}}_topology'
    topology += 'ip netns exec x-ns1 ip a >> ${{EXPORT_FILE}}_topology'
    topology += 'echo -e "\\nip a on x-ns2" >> ${{EXPORT_FILE}}_topology'
    topology += 'ip netns exec x-ns2 ip a >> ${{EXPORT_FILE}}_topology'
    script += topology.format(**settings)

    #script to run
    script += """
    ip netns exec x-ns1 iperf -s &>/dev/null & IPERF_PID=$!
    for i in `seq {repetitions}`; do
        echo -n "Running iperf (with {parallelism} clients) ($i)... "
        sleep 1
        csvline=$(ip netns exec x-ns2 timeout --signal=KILL 20 iperf -c 10.113.1.1 -y C -P {parallelism} | tail -n1)
        if [ "$csvline" ]; then
            measure=${{csvline##*,}}
            echo measured $(numfmt --to=iec --suffix=b/s $measure)
            echo $measure >> $EXPORT_FILE
        else
            echo error
        fi
    done
    kill $IPERF_PID && sleep 1
    """.format(**settings)

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
        for (n_ovs, ovs_ovs_links, ovs_ns_links, parallelism) in itertools.product((0, 1, 2, 3, 5, 10, 20, 30, 50), ('patch', 'veth'), ('port', 'veth'), (1, 2, 4, 8, 12)):
            test(n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, 10)
