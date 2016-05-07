#!/bin/bash
shopt -s nullglob

start_time="$(date +%s)"
start_time=$((start_time - 10))  # ten seconds of error, just to be sure

python iperf_veth_udp.py generate
python iperf_veth_tcp.py generate

python iperf3m_chain_ovs_tcp.py generate

python iperf3m_chain_ns_udp.py generate
python iperf3m_chain_ns_tcp.py generate

python iperf3m_veth_udp_packetsize.py generate

python iperf3m_veth_udp_iptables.py generate

python iperf3m_chain_ns_qdisc_udp.py generate


function find_stale {
    [ ! -z "$1" ] && delete=yes
    count=0
    for script_file in results/*.sh; do
        edit_time=$(stat --format=%Y "$script_file")
        if [ $edit_time -lt $start_time ]; then
            count=$((count + 1))
            if [ "$delete" ]; then
                test_files="$(echo ${script_file%.*}.*)"
                if [ -z "$test_files" ]; then
                    continue
                fi
                rm $test_files
            fi
        fi
    done
    [ ! "$delete" ] && echo $count
}

echo
echo -n "Checking for stale experiments... "
count_stale=$(find_stale)
echo "found $count_stale."
[ "$count_stale" == 0 ] && exit

read -p "Should I delete them? " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    find_stale delete
fi
