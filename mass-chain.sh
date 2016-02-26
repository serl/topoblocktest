#!/bin/bash

for ovs_conn in patch veth; do
    for ns_conn in port veth; do
        for ovses in 0 1 2 3 5 10 20 30 50 99; do
            python chain_ovs.py "$ovses" "$ovs_conn" "$ns_conn" | bash
        done
    done
done
