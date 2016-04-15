import textwrap
from .bash import CommandBlock


def begin():
    script = CommandBlock()
    script += '#!/bin/bash'
    script += 'umask 0000'  # as the script will be run as root, this ensures that after you can play around as normal user ;)
    script += ''
    return script


def counter_increment(**settings):
    return 'counter=$(cat {result_file}.count 2>/dev/null) ; echo $((counter + 1)) > {result_file}.count'.format(**settings)


def iperf2(**in_settings):
    defaults = {
        'tcpdump': False,
        'parallelism': 1,
        'protocol': 'tcp',
        '__udp_param': '',
        'packet_size': 'default',
        '__packet_size_param': '',
        'result_file': None,
        'ns1': None,
        'ns2': None,
        'duration': 30,
    }
    settings = defaults.copy()
    settings.update(in_settings)
    settings['counter_increment'] = counter_increment(**settings)
    if settings['protocol'] == 'udp':
        settings['__udp_param'] = '--udp --bandwidth 100G '  # will generate a warning on the server side, but we don't care
    else:
        settings['protocol'] = 'tcp'
    if settings['packet_size'] != 'default':
        if settings['protocol'] == 'udp':
            settings['__packet_size_param'] = '--len {} '.format(settings['packet_size'])
        else:
            settings['__packet_size_param'] = '--mss {} '.format(settings['packet_size'])
    for key in ('result_file', 'ns1', 'ns2'):
        if settings[key] is None:
            raise ValueError('{} missing'.format(key))
    settings['duration'] = int(settings['duration'])
    if settings['duration'] < 5:
        raise ValueError('Duration must be integer >= 5')
    settings['kill_after'] = settings['duration'] + 15
    settings['iostat_interval'] = 5
    settings['iostat_count'] = settings['duration'] // settings['iostat_interval']

    script = CommandBlock()
    script += textwrap.dedent("""
    mkdir -p `dirname {result_file}`
    ip netns exec {ns1} iperf -s {__udp_param} &>/dev/null & IPERF_PID=$!
    if [ "{tcpdump}" == True ]; then #tcpdump
        ip netns exec {ns1} tcpdump -s 96 -w {result_file}.pcap &>/dev/null & TCPDUMP_PID=$!
    fi
    server_addr=$(ip netns exec {ns1} ip addr show scope global | grep inet | cut -d' ' -f6 | cut -d/ -f1)
    echo -n "Running iperf2 over {protocol} (with {parallelism} clients)... "
    sleep 1
    (LC_ALL=C iostat -c {iostat_interval} {iostat_count} | awk 'FNR==3 {{ header = $0; print }} FNR!=1 && $0 != header && $0' > {result_file}.cpu.temp) & IOSTAT_PID=$! # CPU monitoring
    iperf2out="$(ip netns exec {ns2} timeout --signal=KILL {kill_after} iperf --time {duration} {__udp_param}{__packet_size_param} --client $server_addr --reportstyle C --parallel {parallelism})"
    expected_lines={parallelism}
    wait $IOSTAT_PID
    [ {parallelism} -gt 1 ] && expected_lines=$((expected_lines + 1))
    output_lines=$(echo "$iperf2out" | wc -l)
    if [ $expected_lines == $output_lines ]; then
        echo measured $(numfmt --to=iec --suffix=b/s ${{iperf2out##*,}})
        echo 'begin' >> {result_file}.iperf2
        echo "$iperf2out" >> {result_file}.iperf2
        cat {result_file}.cpu.temp >> {result_file}.cpu
        {counter_increment}
        sleep 5 #let the load decrease
    else
        echo error
    fi
    rm {result_file}.cpu.temp
    kill $IPERF_PID $TCPDUMP_PID
    wait
    sleep 1
    """).format(**settings)
    return script


def iperf3(**in_settings):
    defaults = {
        'tcpdump': False,
        'parallelism': 1,
        'protocol': 'tcp',
        '__udp_param': '',
        'packet_size': 'default',
        '__packet_size_param': '',
        'result_file': None,
        'ns1': None,
        'ns2': None,
        'duration': 30,
        'zerocopy': False,
        '__zerocopy_param': '',
        'affinity': False,
        '__affinity_param': '',
    }
    settings = defaults.copy()
    settings.update(in_settings)
    settings['counter_increment'] = counter_increment(**settings)
    for key in ('result_file', 'ns1', 'ns2'):
        if settings[key] is None:
            raise ValueError('{} missing'.format(key))
    if settings['protocol'] == 'udp':
        settings['__udp_param'] = '--udp --bandwidth 0 '
    else:
        settings['protocol'] = 'tcp'
    if settings['packet_size'] != 'default':
        if settings['protocol'] == 'udp':
            settings['__packet_size_param'] = '--length {} '.format(settings['packet_size'])
        else:
            settings['__packet_size_param'] = '--set-mss {} '.format(settings['packet_size'])
    if settings['zerocopy']:
        settings['__zerocopy_param'] = '--zerocopy '
    if settings['affinity']:
        settings['__affinity_param'] = '--affinity 0,1 '
    settings['duration'] = int(settings['duration'])
    if settings['duration'] < 5:
        raise ValueError('Duration must be integer >= 5')
    settings['kill_after'] = settings['duration'] + 15
    settings['iostat_interval'] = 5
    settings['iostat_count'] = settings['duration'] // settings['iostat_interval']

    script = CommandBlock()
    script += textwrap.dedent("""
    mkdir -p `dirname {result_file}`
    ip netns exec {ns1} iperf3 -s --interval 0 &>/dev/null & IPERF_PID=$!
    if [ "{tcpdump}" == True ]; then #tcpdump
        ip netns exec {ns1} tcpdump -s 96 -w {result_file}.pcap &>/dev/null & TCPDUMP_PID=$!
    fi
    server_addr=$(ip netns exec {ns1} ip addr show scope global | grep inet | cut -d' ' -f6 | cut -d/ -f1)
    echo -n "Running iperf3 over {protocol} (with {parallelism} clients)... "
    sleep 1
    (LC_ALL=C iostat -c {iostat_interval} {iostat_count} | awk 'FNR==3 {{ header = $0; print }} FNR!=1 && $0 != header && $0' > {result_file}.cpu.temp) & IOSTAT_PID=$! # CPU monitoring
    ip netns exec {ns2} timeout --signal=KILL {kill_after} iperf3 --time {duration} --interval 0 {__affinity_param}{__zerocopy_param}{__udp_param}{__packet_size_param} --parallel {parallelism} --client $server_addr --json >> {result_file}.iperf3
    iperf_exitcode=$?
    wait $IOSTAT_PID
    if [ $iperf_exitcode == 0 ]; then
        echo success
        cat {result_file}.cpu.temp >> {result_file}.cpu
        {counter_increment}
        sleep 5 #let the load decrease
    else
        echo error
    fi
    rm {result_file}.cpu.temp
    kill $IPERF_PID $TCPDUMP_PID
    wait
    sleep 1
    """).format(**settings)
    return script


def iperf3m(**in_settings):
    defaults = {
        'tcpdump': False,
        'parallelism': 1,
        'protocol': 'tcp',
        '__udp_param': '',
        'packet_size': 'default',
        '__packet_size_param': '',
        'result_file': None,
        'ns1': None,
        'ns2': None,
        'duration': 30,
        'zerocopy': False,
        '__zerocopy_param': '',
        'affinity': False,
    }
    settings = defaults.copy()
    settings.update(in_settings)
    settings['counter_increment'] = counter_increment(**settings)
    for key in ('result_file', 'ns1', 'ns2'):
        if settings[key] is None:
            raise ValueError('{} missing'.format(key))
    if settings['protocol'] == 'udp':
        settings['__udp_param'] = '--udp --bandwidth 0 '
    else:
        settings['protocol'] = 'tcp'
    if settings['packet_size'] != 'default':
        if settings['protocol'] == 'udp':
            settings['__packet_size_param'] = '--length {} '.format(settings['packet_size'])
        else:
            settings['__packet_size_param'] = '--set-mss {} '.format(settings['packet_size'])
    if settings['zerocopy']:
        settings['__zerocopy_param'] = '--zerocopy '
    settings['duration'] = int(settings['duration'])
    if settings['duration'] < 5:
        raise ValueError('Duration must be integer >= 5')
    settings['kill_after'] = settings['duration'] + 15
    settings['iostat_interval'] = 5
    settings['iostat_count'] = settings['duration'] // settings['iostat_interval']

    script = CommandBlock()
    script += textwrap.dedent("""
    mkdir -p `dirname {result_file}`
    for i in `seq {parallelism}`; do
        PORT=$((5201 + i))
        ip netns exec {ns1} iperf3 -s --interval 0 --port $PORT &>/dev/null & IPERF_PIDs="$IPERF_PIDs $!"
    done
    if [ "{tcpdump}" == True ]; then #tcpdump
        ip netns exec {ns1} tcpdump -s 96 -w {result_file}.pcap &>/dev/null & TCPDUMP_PID=$!
    fi
    server_addr=$(ip netns exec {ns1} ip addr show scope global | grep inet | cut -d' ' -f6 | cut -d/ -f1)
    echo "Running iperf3 over {protocol} (with {parallelism} servers and clients)... "
    sleep 1
    (LC_ALL=C iostat -c {iostat_interval} {iostat_count} | awk 'FNR==3 {{ header = $0; print }} FNR!=1 && $0 != header && $0' >> {result_file}.cpu) & IOSTAT_PID=$! # CPU monitoring
    for i in `seq {parallelism}`; do
        PORT=$((5201 + i))
        if [ "{affinity}" == True ]; then #affinity
            NPROC=$(nproc)
            PROC_CLIENT=$(( (i - 1) % NPROC ))
            PROC_SERVER=$(( (i - 1 + {parallelism}) % NPROC ))
            AFFINITY="--affinity $PROC_CLIENT,$PROC_SERVER"
        fi
        (ip netns exec {ns2} timeout --signal=KILL {kill_after} iperf3 --time {duration} --interval 0 $AFFINITY {__zerocopy_param}{__udp_param}{__packet_size_param} --client $server_addr --port $PORT --json >> {result_file}.iperf3.$i) &
        CLIENT_IPERF_PIDs="$CLIENT_IPERF_PIDs $!"
    done
    wait $IOSTAT_PID $CLIENT_IPERF_PIDs
    {counter_increment}
    sleep 5 #let the load decrease
    kill $IPERF_PIDs $TCPDUMP_PID
    wait
    sleep 1
    """).format(**settings)
    return script
