from lib import plot

colors = {
    'patch-port': 'red',
    'patch-veth': 'blue',
    'veth-port': 'green',
    'veth-veth': 'black',
}

plot.iperf('results/chain_ovs_iperf/', colors=colors)
