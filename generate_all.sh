#!/bin/bash

python iperf_veth_udp.py generate
python iperf_veth_tcp.py generate

python iperf3m_chain_ovs_tcp.py generate

python iperf3m_chain_ns_udp.py generate
python iperf3m_chain_ns_tcp.py generate

python iperf3m_veth_udp_packetsize.py generate
