#!/bin/bash

python generate_iperf_veth.py
python generate_iperf_chain_ovs.py
python generate_iperf_chain_ns.py
python generate_iperf_compare_chain_ns.py
