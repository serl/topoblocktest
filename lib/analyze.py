import re
import pathlib
import itertools
import json
import warnings
warnings.formatwarning = lambda message, category, *a: '{}: {}\n'.format(category.__name__, message)
from .math_utils import mean_confidence, jain_fairness
from collections import OrderedDict


def iostat_cpu(directory, settings_hash):
    with directory.joinpath(settings_hash + '.cpu').open() as file_handler:
        keys = ('user', 'nice', 'system', 'iowait', 'steal', 'idle')
        values_list = [[], [], [], [], [], []]
        skip_line = False
        for line in file_handler:
            if skip_line or line.startswith('avg-cpu:'):
                skip_line = not skip_line  # if there's avg-cpu, we skip two lines
                continue
            row = map(float, line.split())
            for i, v in enumerate(row):
                values_list[i].append(v)
        cpu = {keys[i]: mean_confidence(values) for i, values in enumerate(values_list)}
        return cpu


def iperf2(directory, settings_hash, settings):
    with directory.joinpath(settings_hash + '.iperf2').open() as file_handler:
        tests = []
        cur_test = None  # it is instantiated and added to `tests` each time the keywork `begin` is read from the file
        for line in file_handler:
            if line.rstrip() == 'begin':
                cur_test = []
                tests.append(cur_test)
            else:
                cur_test.append(line.rstrip().split(','))
    throughputs = []
    fairnesses = []
    for test in tests:
        if settings['parallelism'] == 1:
            if len(test) != 1:
                raise ValueError('For test {}, the result sounds strange (parallelism 1, but {} lines in the csv).'.format(settings_hash, len(test)))
            throughputs.append(float(test[0][8]))
            fairnesses.append(1)
        else:
            if len(test) != settings['parallelism'] + 1:
                raise ValueError('For test {}, the result sounds strange (parallelism {}, but {} lines in the csv).'.format(settings_hash, settings['parallelism'], len(test)))
            bytes_list = [int(x[7]) for x in test[:-1]]
            bytes_sum = sum(bytes_list)
            bytes_total = int(test[-1][7])
            iperf_throughput = float(test[-1][8])
            if bytes_sum != bytes_total:
                raise ValueError('For test {}, the result sounds strange (sum of transfers {}, but master result {}).'.format(settings_hash, bytes_sum, bytes_total))

            durations = set([x[6] for x in test])
            if len(durations) > 1:
                warnings.warn('For test {}, the transfers have different durations: {}.'.format(settings_hash, durations), RuntimeWarning)
            # as this previous warning actually pops out, maybe it's better to stick on iperf output for throughput and not calculate it by myself, as in the next three lines
            # t_begin, t_end = map(float, test[-1][6].split('-'))
            # duration = t_end - t_begin
            # throughputs.append(8.0 * bytes_total / duration)
            throughputs.append(iperf_throughput)
            fairnesses.append(jain_fairness(bytes_list))
    return {
        'throughput': mean_confidence(throughputs),
        'fairness': mean_confidence(fairnesses),
    }


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
        throughputs.append(8.0 * json_end['sum_received']['bytes'] / json_end['sum_received']['seconds'])
        cpu_utilizations.append((json_end['cpu_utilization_percent']['host_total'], json_end['cpu_utilization_percent']['remote_total']))
        bytes_streams = [stream['receiver']['bytes'] for stream in json_end['streams']]
        fairnesses.append(jain_fairness(bytes_streams))
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
            throughput += 8.0 * json_end['sum_received']['bytes'] / json_end['sum_received']['seconds']
            bytes_streams.append(json_end['sum_received']['bytes'])
        throughputs.append(throughput)
        fairnesses.append(jain_fairness(bytes_streams))
    return {
        'throughput': mean_confidence(throughputs),
        #'cpu': not clear: how should I interpret the results from iperf3?
        'fairness': mean_confidence(fairnesses),
    }


def get_chain_analysis(db_query, row_info_fn, grouping_fn=lambda row_element: (0,)):
    columns = sorted(list(set((r['chain_len'] for r in db_query))))
    rows = {}  # key => {label => label of the serie, color => color, row => [db record, ...]}
    for r in db_query:
        key, label, color = row_info_fn(r)
        if key not in rows:
            rows[key] = {'label': label, 'color': color, 'row': [None] * len(columns)}
        col_index = columns.index(r['chain_len'])
        if rows[key]['row'][col_index] is not None:
            raise ValueError("Multiple values for serie '{}' at chain_len '{}'.\nHere's the two we have now:\n{}\nand\n{}".format(label, r['chain_len'], r, rows[key]['row'][col_index]))
        rows[key]['row'][col_index] = r

    rows_sorted = OrderedDict()  # label => {label => label of the serie, color => color, row => [db record, ...]}
    rows_grouped = {}  # group_id => OrderedDict(*as above*)
    for k in sorted(rows.keys()):
        row = rows[k]
        rows_sorted[row['label']] = row
        first_obj = [c for c in row['row'] if c is not None][0]
        for group_id in grouping_fn(first_obj):
            if group_id not in rows_grouped:
                rows_grouped[group_id] = OrderedDict()
            rows_grouped[group_id][row['label']] = row
    rows_grouped_sorted = OrderedDict([(i, rows_grouped[i]) for i in sorted(rows_grouped.keys())])

    return columns, rows_sorted, rows_grouped_sorted
