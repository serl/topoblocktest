from .bash import CommandBlock

def begin():
    script = CommandBlock()
    script += '#!/bin/bash'
    script += 'umask 0000' #as the script will be run as root, this ensures that after you can play around as normal user ;)
    script += ''
    return script

def iperf(**in_settings):
    defaults = {
        'repetitions': 1,
        'tcpdump': False,
        'parallelism': 1,
        'mss': 'default',
        '__mss_param': '',
        'result_file': None,
        'ns1': None,
        'ns2': None,
        'duration': 30,
    }
    settings = defaults.copy()
    settings.update(in_settings)
    if settings['mss'] != 'default':
        settings['__mss_param'] = '--mss {}'.format(settings['mss'])
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
    script += """
    mkdir -p `dirname {result_file}`
    ip netns exec {ns1} iperf -s &>/dev/null & IPERF_PID=$!
    if [ "{tcpdump}" == True ]; then
        ip netns exec {ns1} tcpdump -s 96 -w {result_file}.pcap &>/dev/null & TCPDUMP_PID=$!
    fi
    server_addr=$(ip netns exec {ns1} ip addr show scope global | grep inet | cut -d' ' -f6 | cut -d/ -f1)
    for i in `seq {repetitions}`; do
        echo -n "Running iperf (with {parallelism} clients) ($i)... "
        sleep 1
        (LC_ALL=C iostat -c {iostat_interval} {iostat_count} | awk 'FNR==3 {{ header = $0; print }} FNR!=1 && $0 != header && $0' >> {result_file}.cpu) & IOSTAT_PID=$! # CPU monitoring
        csvline=$(ip netns exec {ns2} timeout --signal=KILL {kill_after} iperf --time {duration} {__mss_param} --client $server_addr --reportstyle C --parallel {parallelism} | tail -n1)
        if [ "$csvline" ]; then
            measure=${{csvline##*,}}
            echo measured $(numfmt --to=iec --suffix=b/s $measure)
            echo $measure >> {result_file}.throughput
            sleep 5 #let the load decrease
        else
            echo error
        fi
        wait $IOSTAT_PID
    done
    kill $IPERF_PID $TCPDUMP_PID
    wait
    sleep 1
    """.format(**settings)
    return script
