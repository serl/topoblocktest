from lib import plot

colors = {
    'direct-veth': 'purple',
    'ovs-port': 'green',
    'ovs-veth': 'black',
}

plot.iperf('results/chain_ns_iperf/', colors=colors)
