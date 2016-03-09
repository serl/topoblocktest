import sys, itertools
import lib.topologies as topologies
from lib.bash import CommandBlock
from datetime import datetime, timedelta

def test(n_ovs, ovs_ovs_links, ovs_ns_links, parallelism=1, repetitions=1, mss=None, disable_offloading=False, tcpdump=False):
    settings = {
        'id': 'chain',
        'n_ovs': int(n_ovs),
        'ovs_ovs_links': ovs_ovs_links,
        'ovs_ns_links': ovs_ns_links,
        'repetitions': repetitions,
        'parallelism': parallelism,
        'mss': mss,
        'mss_param': '',
        'disable_offloading': disable_offloading,
        'tcpdump': tcpdump,
    }
    if settings['mss'] is not None:
        settings['mss_param'] = '--mss {}'.format(settings['mss'])

    settings['test_dir'] = 'results/chain_ovs_iperf/'
    if settings['disable_offloading']:
        settings['test_dir'] += 'disable_offloading/'
    else:
        settings['test_dir'] += 'enable_offloading/'
    if settings['mss'] is None:
        settings['test_dir'] += 'default/'
    else:
        settings['test_dir'] += '{}/'.format(settings['mss'])

    m = topologies.ovs_chain(settings['n_ovs'], settings['ovs_ovs_links'], settings['ovs_ns_links'], settings['disable_offloading'])

    script = CommandBlock()
    script += '#!/bin/bash'
    script += m.get_script()
    script += ''
    script += 'umask 0000' #as the script will be run as root, this ensures that after you can play around as normal user ;)
    script += 'TEST_DIR="{test_dir}"'.format(**settings)
    script += 'EXPORT_FILE="$TEST_DIR/{id}-{parallelism}-{n_ovs}-{ovs_ovs_links}-{ovs_ns_links}"'.format(**settings)
    script += 'CPU_FILE="${EXPORT_FILE}_cpu"'
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
    if [ "{tcpdump}" == True ]; then
        ip netns exec x-ns2 tcpdump -s 96 -w $EXPORT_FILE.pcap &>/dev/null & TCPDUMP_PID=$!
    fi
    for i in `seq {repetitions}`; do
        echo -n "Running iperf (with {parallelism} clients) ($i)... "
        sleep 1
        (LC_ALL=C iostat -c 5 6 | awk 'FNR==3 {{ header = $0; print }} FNR!=1 && $0 != header && $0' >> $CPU_FILE) & IOSTAT_PID=$! # CPU monitoring
        csvline=$(ip netns exec x-ns2 timeout --signal=KILL 45 iperf --time 30 {mss_param} --client 10.113.1.1 --reportstyle C --parallel {parallelism} | tail -n1)
        if [ "$csvline" ]; then
            measure=${{csvline##*,}}
            echo measured $(numfmt --to=iec --suffix=b/s $measure)
            echo $measure >> $EXPORT_FILE
            sleep 5 #let the load decrease
        else
            echo error
        fi
        wait $IOSTAT_PID
    done
    kill $IPERF_PID $TCPDUMP_PID
    wait
    sleep 1
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
        repetitions = 10
        cases = []
        for (n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, mss, disable_offloading) in itertools.product((0, 1, 2, 3, 5, 10, 20, 30, 50), ('patch', 'veth'), ('port', 'veth'), (1, 2, 4, 8, 12), (None, 536), (True, False)):
            if n_ovs is 0 and (ovs_ovs_links != 'veth' or ovs_ns_links != 'veth'):
                continue
            if (mss is not None or disable_offloading) and parallelism != 4:
                continue
            cases.append((n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, mss, disable_offloading))

        print('{} experiments to do. Expected end: {}\n'.format(len(cases), datetime.now() + timedelta(seconds=len(cases)*2 + len(cases)*repetitions*35)))
        for (n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, mss, disable_offloading) in cases:
            test(n_ovs, ovs_ovs_links, ovs_ns_links, parallelism, 10, mss, disable_offloading)
