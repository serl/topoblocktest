#!/bin/bash
export LC_ALL=C

if ! [ "$1" ]; then
  echo "Usage: $0 <pcap file>"
  echo "It will produce a report about packet sizes."
  exit 1
fi

exec tshark -r "$1" -Y 'tcp.len > 0' -T fields -E separator=, -e tcp.len | sort | uniq -c | sort -nr | head -n10
