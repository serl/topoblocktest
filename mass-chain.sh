#!/bin/bash

for ovses in 1 2 3 5 10 20 30 50; do
    python chain_ovs.py "$ovses" "$@" | bash
done
