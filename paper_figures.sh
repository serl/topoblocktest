#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <OUTPUT_DIR>"
    exit 1
fi

OUTPUT_DIR="$1"

# TCP / veth
python iperf_veth_tcp.py --filter paper --plot-y-axes throughput --plot-legend-loc 'lower right' --out $OUTPUT_DIR/iperf_veth_tcp.svg --plot-size-factor 1,0.7  # fig 1
# python iperf_veth_tcp.py --filter paper --plot-y-axes throughput --plot-legend-loc 'lower right' --relative-to zerocopy=False --out $OUTPUT_DIR/iperf_veth_tcp_rel_zerocopy.svg

# UDP / veth
python iperf3m_veth_udp_packetsize.py --filter paper --plot-y-axes throughput --plot-legend-loc 'upper left' --out $OUTPUT_DIR/iperf_veth_udp_packetsize_throughput.svg --plot-size-factor 1,0.9 # fig 2
python iperf3m_veth_udp_packetsize.py --filter paper --plot-y-axes packetput --out $OUTPUT_DIR/iperf_veth_udp_packetsize_packetput.svg --plot-size-factor 1,0.9 # fig 3

# OvS
python iperf3m_chain_ovs_tcp.py --filter paper --plot-y-axes throughput:30000000000,200000000000 --out $OUTPUT_DIR/iperf_chain_ovs_tcp.svg # fig 5
# python iperf3m_chain_ovs_tcp.py --filter paper --plot-y-axes throughput:-60,30 --relative-to ovs_ovs_links=patch ovs_ns_links=port --out $OUTPUT_DIR/iperf_chain_ovs_tcp_rel_patchport.svg

# NS
python iperf3m_chain_ns_tcp.py --filter paper --plot-y-axes throughput --out $OUTPUT_DIR/iperf_chain_ns_tcp.svg # fig 7
# python iperf3m_chain_ns_tcp.py --filter paper --plot-y-axes throughput --relative-to use_ovs=False ovs_ns_links=veth chain_len=2 --out $OUTPUT_DIR/iperf_chain_ns_tcp_rel_chainlen2.svg
python iperf3m_chain_ns_udp.py --filter paper-parallelism --plot-y-axes throughput --out $OUTPUT_DIR/iperf_chain_ns_udp.svg --plot-size-factor 1,0.87 # fig 8
# python iperf3m_chain_ns_udp.py --filter paper-8 --plot-y-axes throughput --out $OUTPUT_DIR/iperf_chain_ns_udp_8flows.svg
# python iperf3m_chain_ns_udp.py --filter paper-6 --plot-y-axes throughput --out $OUTPUT_DIR/iperf_chain_ns_udp_6flows.svg

# iptables
python iperf3m_veth_udp_iptables.py --filter paper --plot-y-axes throughput --out $OUTPUT_DIR/iperf_veth_udp_iptables.svg # fig 9
# python iperf3m_chain_ns_iptables_udp.py --filter paper_10 --plot-y-axes throughput --relative-to iptables_rules_len=0 --out $OUTPUT_DIR/iperf_chain_ns_iptables_udp_10.svg
# python iperf3m_chain_ns_iptables_udp.py --filter paper_100 --plot-y-axes throughput --relative-to iptables_rules_len=0 --out $OUTPUT_DIR/iperf_chain_ns_iptables_udp_100.svg
python iperf3m_chain_ns_iptables_fixed_udp.py --filter 100 --plot-y-axes throughput --out $OUTPUT_DIR/iperf_chain_ns_iptables_fixed_udp_100.svg --plot-size-factor 1,0.9 # fig 10a
python iperf3m_chain_ns_iptables_fixed_udp.py --filter 1000 --plot-y-axes throughput:0,50000000000 --out $OUTPUT_DIR/iperf_chain_ns_iptables_fixed_udp_1000.svg --plot-size-factor 1,0.9 # fig 10b
python iperf3m_chain_ns_iptables_fixed_udp.py --filter 5000 --plot-y-axes throughput:0,20000000000 --out $OUTPUT_DIR/iperf_chain_ns_iptables_fixed_udp_5000.svg --plot-size-factor 1,0.9 # fig 10c

# qdisc
python iperf3m_chain_ns_qdisc_udp.py --filter paper --plot-y-axes throughput --out $OUTPUT_DIR/iperf_chain_ns_qdisc_udp.svg --plot-size-factor 1,0.8 # fig 11
# python iperf3m_chain_ns_qdisc_udp.py --filter paper --plot-y-axes throughput --relative-to topology=ns_chain --out $OUTPUT_DIR/iperf_chain_ns_qdisc_udp_rel_noqdisc.svg
