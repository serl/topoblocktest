import re
import pathlib
import itertools
import json
from .math_utils import mean_confidence
from collections import OrderedDict


def iostat_cpu(directory, settings_hash):
    with directory.joinpath(settings_hash + '.cpu').open() as file_handler:
        keys = ('user', 'nice', 'system', 'iowait', 'steal', 'idle')
        values_list = [[], [], [], [], [], []]
        len_values_check = 0
        skip_line = False
        for line in file_handler:
            if skip_line or line.startswith('avg-cpu:'):
                skip_line = not skip_line  # if there's avg-cpu, we skip two lines
                len_values_check += 0.5  # as we do it twice
                continue
            row = map(float, line.split())
            for i, v in enumerate(row):
                values_list[i].append(v)
        cpu = {keys[i]: mean_confidence(values) for i, values in enumerate(values_list)}
        return cpu


def iperf(directory, settings_hash, settings):
    with directory.joinpath(settings_hash + '.throughput').open() as file_handler:
        values = [int(line.rstrip()) for line in file_handler]
    return {'throughput': mean_confidence(values)}


def read_jsons(file_handler):
    # read all from file_handler, splitting
    json_strings = []
    current_json = ''
    for line in file_handler:
        if line.startswith('{'):
            if len(current_json):
                json_strings.append(current_json)
            current_json = line
        else:
            current_json += line
    json_strings.append(current_json)  # the last one, don't forget this poor guy!
    # do the actual conversion from json to Python dict
    json_dicts = []
    for json_str in json_strings:
        json_dicts.append(json.loads(json_str))
    return json_dicts


def iperf3(directory, settings_hash, settings):
    with directory.joinpath(settings_hash + '.iperf3').open() as file_handler:
        json_dicts = read_jsons(file_handler)
    throughputs = []
    cpu_utilizations = []
    fairnesses = []
    for json_dict in json_dicts:
        json_end = json_dict['end']
        throughputs.append(json_end['sum_received']['bytes'] / json_end['sum_received']['seconds'] * 8)
        cpu_utilizations.append((json_end['cpu_utilization_percent']['host_total'], json_end['cpu_utilization_percent']['remote_total']))
        bytes_streams = [stream['receiver']['bytes'] for stream in json_end['streams']]
        fairnesses.append(sum(bytes_streams)**2 / (len(bytes_streams) * sum([x**2 for x in bytes_streams])))  # Jain's fairness index
    return {
        'throughput': mean_confidence(throughputs),
        'cpu': {'host': mean_confidence([x[0] for x in cpu_utilizations]), 'remote': mean_confidence([x[1] for x in cpu_utilizations])},
        'fairness': mean_confidence(fairnesses),
    }


def iperf3m(directory, settings_hash, settings):
    json_dicts = [None] * settings['parallelism']
    for i in range(settings['parallelism']):
        with directory.joinpath('{}.iperf3.{}'.format(settings_hash, i + 1)).open() as file_handler:
            json_dicts[i] = read_jsons(file_handler)
            if i > 0 and len(json_dicts[i - 1]) != len(json_dicts[i]):
                raise ValueError('Something went wrong on {}: I expected to have the same number of tests on all the threads.'.format(settings_hash))
    tests_count = len(json_dicts[i])
    throughputs = []
    fairnesses = []
    for test_num in range(tests_count):
        throughput = 0
        bytes_streams = []
        for thread_id in range(settings['parallelism']):
            json_end = json_dicts[thread_id][test_num]['end']
            throughput += json_end['sum_received']['bytes'] / json_end['sum_received']['seconds'] * 8
            bytes_streams.append(json_end['sum_received']['bytes'])
        throughputs.append(throughput)
        fairnesses.append(sum(bytes_streams)**2 / (len(bytes_streams) * sum([x**2 for x in bytes_streams])))  # Jain's fairness index
    return {
        'throughput': mean_confidence(throughputs),
        #'cpu': not clear: how should I interpret the results from iperf3?
        'fairness': mean_confidence(fairnesses),
    }
