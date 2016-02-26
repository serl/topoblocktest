import sys
from lib.topology import Master, OVS, Netns, Link

try:
    settings = {
        'id': 'chain',
        'n_ovs': int(sys.argv[1]),
        'ovs_ovs': sys.argv[2],
        'ovs_ns': sys.argv[3],
    }
except (IndexError, ValueError):
    print('usage: {} <number_of_ovs_to_chain> <link_type_between_ovs: patch or veth> <link_type_between_ovs_and_ns: port or veth>'.format(sys.argv[0]), file=sys.stderr)
    raise

m = Master()

ns1 = Netns('x-ns1').add_to(m)
ns2 = Netns('x-ns2').add_to(m)

if settings['n_ovs'] > 0:
    ovss = []
    for i_ovs in range(settings['n_ovs']):
        ovss.append(OVS().add_to(m))

    #and link them
    for ovs1, ovs2 in zip(ovss, ovss[1:]):
        Link.declare(ovs1, ovs2, link_type=settings['ovs_ovs'])

    Link.declare((ns1, '10.113.1.1'), ovss[0], link_type=settings['ovs_ns'])
    Link.declare((ns2, '10.113.1.2'), ovss[-1], link_type=settings['ovs_ns'])

else:
    Link.declare((ns1, '310.113.1.1'), (ns2, '10.113.1.2'))

topo_definitions = m.get_script()


script = '#!/bin/bash\n'+topo_definitions+'trap opg_cleanup EXIT\nopg_setup\n'
#topology check
topology = 'ovs-vsctl show > results/{id}-{n_ovs}-{ovs_ovs}-{ovs_ns}_topology\n'
topology += 'echo -e "\\nip a on x-ns1" >> results/{id}-{n_ovs}-{ovs_ovs}-{ovs_ns}_topology\n'
topology += 'ip netns exec x-ns1 ip a >> results/{id}-{n_ovs}-{ovs_ovs}-{ovs_ns}_topology\n'
topology += 'echo -e "\\nip a on x-ns2" >> results/{id}-{n_ovs}-{ovs_ovs}-{ovs_ns}_topology\n'
topology += 'ip netns exec x-ns2 ip a >> results/{id}-{n_ovs}-{ovs_ovs}-{ovs_ns}_topology\n'

script += topology.format(**settings)

settings['repetitions'] = 10
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
        echo $measure >> results/{id}-{n_ovs}-{ovs_ovs}-{ovs_ns}
    done
    kill $IPERF_PID && sleep 1
    """.format(**settings) #--mss {mss} seems not to work :/

print(script)
