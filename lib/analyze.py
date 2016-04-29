import re
import pathlib
import itertools
import json
import warnings
warnings.formatwarning = lambda message, category, *a: '{}: {}\n'.format(category.__name__, message)
from .math_utils import mean_confidence, jain_fairness
from collections import OrderedDict


class AnalysisException(Exception):

    def __init__(self, message, test_hash):
        super(AnalysisException, self).__init__(message)
        self.test_hash = test_hash


def checked_mean_confidence(throughputs, settings_hash):
    if len(throughputs) == 0:
        return None
    throughput_meanconf = mean_confidence(throughputs)
    if 2 * throughput_meanconf[1] > throughput_meanconf[0]:
        warnings.warn('For test {}, the conf interval for throughput is huge. Raw values: {}'.format(settings_hash, throughputs), RuntimeWarning)
    return throughput_meanconf


def count(directory, settings_hash):
    count = 0
    try:
        with directory.joinpath(settings_hash + '.count').open() as count_fh:
            count = int(count_fh.read())
    except (FileNotFoundError, ValueError):
        pass
    return count


def iostat_cpu(directory, settings_hash):
    try:
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
    except FileNotFoundError:
        return None, 0

    cpu = {keys[i]: mean_confidence(values) for i, values in enumerate(values_list)}
    if int(len_values_check) != len_values_check:
        raise AnalysisException('For test {}, the iostat output is buggy ({} tests).'.format(settings_hash, len_values_check), settings_hash)
    return cpu, int(len_values_check)


def iperf2(directory, settings_hash, settings):
    csv_fields = ['timestamp', 'clientIp', 'clientPort', 'serverIp', 'serverPort', 'transferId', 'timing', 'bytes', 'throughput', 'jitter', 'errors', 'datagrams', 'errorRatio', 'outOfOrder']
    try:
        with directory.joinpath(settings_hash + '.iperf2').open() as file_handler:
            tests = []
            cur_test = None  # it is instantiated and added to `tests` each time the keywork `begin` is read from the file
            for line in file_handler:
                if line.rstrip() == 'begin':
                    cur_test = []
                    tests.append(cur_test)
                else:
                    linedict = {}
                    for i, val in enumerate(line.rstrip().split(',')):
                        linedict[csv_fields[i]] = val
                    linedict['startTime'], linedict['endTime'] = map(float, linedict['timing'].split('-'))
                    linedict['duration'] = linedict['endTime'] - linedict['startTime']
                    cur_test.append(linedict)
    except FileNotFoundError:
        return None, 0

    throughputs = []
    packetputs = []
    fairnesses = []
    for test in tests:
        expected_lines = settings['parallelism']
        mode = 'tcp'  # actually it is used even on udp with smaller packets, see the next line ;)
        if settings['protocol'] == 'udp' and settings['packet_size'] >= 52:
            expected_lines *= 2
            mode = 'udp'
        if settings['parallelism'] > 1:
            expected_lines += 1
        if len(test) != expected_lines:
            raise AnalysisException('For test {}, the result sounds strange (parallelism {}, but {} lines in the csv, while {} expected).'.format(settings_hash, settings['parallelism'], len(test), expected_lines), settings_hash)
        if settings['parallelism'] == 1:
            if len(test) == 2:  # udp and not legacy mode (packet_size >= 52)
                throughputs.append(float(test[1]['throughput']))
                packetputs.append(float(test[1]['datagrams']) / test[1]['duration'])
            else:
                throughputs.append(float(test[0]['throughput']))
            fairnesses.append(1)
        else:
            summary_lines = [l for l in test if l['transferId'] == '-1']
            if len(summary_lines) != 1:
                raise AnalysisException('For test {}, the result sounds strange (we have {} summary lines, instead of 1).'.format(settings_hash, len(master_lines)), settings_hash)
            summary_line = summary_lines[0]

            flow_lines = [l for l in test if l != summary_line]
            if mode == 'udp':
                flow_lines = [l for l in flow_lines if 'datagrams' in l]  # an udp line has the 'datagrams field

            bytes_list = [int(x['bytes']) for x in flow_lines]
            for n_bytes in [b for b in bytes_list if b < 0]:
                raise AnalysisException('For test {}, the result sounds strange (we have one transfer of {} packets; that is a negative number).'.format(settings_hash, n_bytes), settings_hash)

            if mode == 'tcp':
                bytes_sum = sum(bytes_list)
                bytes_total = int(summary_line['bytes'])
                iperf_throughput = float(summary_line['throughput'])
                if bytes_sum != bytes_total:
                    raise AnalysisException('For test {}, the result sounds strange (sum of transfers {}, but master result {}).'.format(settings_hash, bytes_sum, bytes_total), settings_hash)

                durations = set([x['timing'] for x in test])
                if len(durations) > 1:
                    warnings.warn('For test {}, the transfers have different durations: {}.'.format(settings_hash, durations), RuntimeWarning)
                # as this previous warning actually pops out sometimes, maybe it's better to stick on iperf output for throughput and not calculate it by myself, as it was in the next line
                # throughputs.append(8.0 * bytes_total / summary_line['duration'])
                throughputs.append(iperf_throughput)

            else:  # mode == 'udp'
                throughput = 0
                packetput = 0
                for line in flow_lines:
                    throughput += 8.0 * float(line['bytes']) / line['duration']
                    try:
                        packetput += float(line['datagrams']) / line['duration']
                    except KeyError:
                        print(settings_hash)
                        raise
                throughputs.append(throughput)
                packetputs.append(packetput)

            fairnesses.append(jain_fairness(bytes_list))
    return {
        'throughput': checked_mean_confidence(throughputs, settings_hash),
        'packetput': checked_mean_confidence(packetputs, settings_hash),
        'fairness': mean_confidence(fairnesses),
    }, len(tests)


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
    try:
        with directory.joinpath(settings_hash + '.iperf3').open() as file_handler:
            json_dicts = read_jsons(file_handler)
    except FileNotFoundError:
        return None, 0

    sum_key = 'sum' if settings['protocol'] == 'udp' else 'sum_received'
    throughputs = []
    packetputs = []
    cpu_utilizations = []
    fairnesses = []
    for json_dict in json_dicts:
        json_end = json_dict['end']
        throughputs.append(8.0 * json_end[sum_key]['bytes'] / json_end[sum_key]['seconds'])
        if settings['protocol'] == 'udp':
            packetputs.append(json_end[sum_key]['packets'] / json_end[sum_key]['seconds'])
        cpu_utilizations.append((json_end['cpu_utilization_percent']['host_total'], json_end['cpu_utilization_percent']['remote_total']))
        bytes_streams = [stream['udp' if settings['protocol'] == 'udp' else 'receiver']['bytes'] for stream in json_end['streams']]
        if len(bytes_streams) != settings['parallelism']:
            raise AnalysisException('For test {}, the result sounds strange (parallelism {}, but {} transfers reported).'.format(settings_hash, settings['parallelism'], len(bytes_streams)), settings_hash)
        for n_bytes in [b for b in bytes_streams if b < 0]:
            raise AnalysisException('For test {}, the result sounds strange (we have one transfer of {} packets; that is a negative number).'.format(settings_hash, n_bytes), settings_hash)
        fairnesses.append(jain_fairness(bytes_streams))
    return {
        'throughput': checked_mean_confidence(throughputs, settings_hash),
        'packetput': checked_mean_confidence(packetputs, settings_hash),
        'cpu': {'host': mean_confidence([x[0] for x in cpu_utilizations]), 'remote': mean_confidence([x[1] for x in cpu_utilizations])},
        'fairness': mean_confidence(fairnesses),
    }, len(json_dicts)


def iperf3m(directory, settings_hash, settings):
    json_dicts = [None] * settings['parallelism']
    for i in range(settings['parallelism']):
        try:
            with directory.joinpath('{}.iperf3.{}'.format(settings_hash, i + 1)).open() as file_handler:
                json_dicts[i] = read_jsons(file_handler)
                if i > 0 and len(json_dicts[i - 1]) != len(json_dicts[i]):
                    raise AnalysisException('Something went wrong on {}: I expected to have the same number of tests on all the workers.'.format(settings_hash), settings_hash)
        except FileNotFoundError:
            if i == 0:
                return None, 0
            else:
                raise AnalysisException('Something went wrong on {}: The number of workers ({}) is different from the requested parallelism ({}).'.format(settings_hash, i + 1, settings['parallelism']), settings_hash)
    tests_count = len(json_dicts[i])
    sum_key = 'sum' if settings['protocol'] == 'udp' else 'sum_received'
    throughputs = []
    packetputs = []
    fairnesses = []
    for test_num in range(tests_count):
        throughput = 0
        packetput = 0
        bytes_streams = []
        for thread_id in range(settings['parallelism']):
            json_end = json_dicts[thread_id][test_num]['end']
            n_bytes = json_end[sum_key]['bytes']
            if n_bytes < 0:
                raise AnalysisException('For test {}, the result sounds strange (we have one transfer of {} packets; that is a negative number).'.format(settings_hash, n_bytes), settings_hash)
            throughput += 8.0 * n_bytes / json_end[sum_key]['seconds']
            if settings['protocol'] == 'udp':
                packetput += json_end[sum_key]['packets'] / json_end[sum_key]['seconds']
            bytes_streams.append(n_bytes)
        throughputs.append(throughput)
        packetputs.append(packetput)
        fairnesses.append(jain_fairness(bytes_streams))
    return {
        'throughput': checked_mean_confidence(throughputs, settings_hash),
        'packetput': checked_mean_confidence(packetputs, settings_hash),
        #'cpu': not clear: how should I interpret the results from iperf3?
        'fairness': mean_confidence(fairnesses),
    }, tests_count


def get_analysis_table(db_query, x_axis, row_info_fn, grouping_fn=None):
    if grouping_fn is None:
        grouping_fn = lambda row_element: (0,)
    columns = sorted(list(set((r[x_axis] for r in db_query))))
    rows = {}  # key => {label => label of the serie, row => [db record, ...]}
    for r in db_query:
        key, label = row_info_fn(r)
        if key not in rows:
            rows[key] = {'label': label, 'row': [None] * len(columns)}
        col_index = columns.index(r[x_axis])
        if rows[key]['row'][col_index] is not None:
            raise ValueError("Multiple values for serie '{}' at '{}' '{}'.\nHere's the two we have now:\n{}\nand\n{}".format(label, x_axis, r[x_axis], r, rows[key]['row'][col_index]))
        rows[key]['row'][col_index] = r

    rows_sorted = OrderedDict()  # label => {label => label of the serie, row => [db record, ...]}
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
