import re
import os
import os.path
import pathlib
import json
import hashlib
import random
import itertools
from . import topologies
from . import tests
from . import analyze
from lib.bash import CommandBlock
from pydblite import Base
import warnings
warnings.formatwarning = lambda message, category, *a: '{}: {}\n'.format(category.__name__, message)

results_dir = 'results/'


def generate_combinations(constants, variables, skip_fn=lambda x: False):
    n = 0
    variables_keys = tuple(variables.keys())
    for combi in itertools.product(*variables.values()):
        settings = constants.copy()
        for i, value in enumerate(combi):
            settings[variables_keys[i]] = value
        if len(settings) is 0:
            continue
        if not skip_fn(settings):
            generate(**settings)
            n += 1
    print('Generated {} cases. Now go and run run_test.py in order to run them!'.format(n))


def generate(**settings):
    settings_json = json.dumps(settings, sort_keys=True)
    settings_hash = hashlib.sha1(settings_json.encode('utf-8')).hexdigest()

    m, ns1, ns2 = getattr(topologies, settings['topology'])(**settings)
    settings['ns1'] = ns1
    settings['ns2'] = ns2

    settings['result_file'] = results_dir
    # if settings['collection'] is not None:
    #     settings['result_file'] += settings['collection'] + '/'
    settings['result_file'] += settings_hash

    script = tests.begin()
    script += m.get_script()
    script += getattr(tests, settings['iperf_name'])(**settings)

    with open(settings['result_file'] + '.config', 'w') as f:
        f.write(settings_json)
    with open(settings['result_file'] + '.sh', 'w') as f:
        f.write(str(script))
    os.chmod(settings['result_file'] + '.sh', 0o777)

    return settings_hash, script


def run_all(target_repetitions=0, dry_run=False, debug=False, recursion_limit=50):
    if not hasattr(run_all, "scripts"):
        run_all.scripts = {}  # hash => CommandBlock instance
    to_run = []  # each script will appear N times, so to reach the target_repetitions
    p = pathlib.Path(results_dir)
    max_count = 0
    forecast_time = 0
    for script_file in p.glob('*.sh'):
        settings_hash = script_file.stem
        count = 0
        try:
            with script_file.parent.joinpath(settings_hash + '.count').open() as count_fh:
                count = int(count_fh.read())
        except (FileNotFoundError, ValueError):
            pass
        max_count = max(max_count, count)
        needed_repetitions = target_repetitions - count
        if needed_repetitions > 0:
            with script_file.open() as script_fh:
                run_all.scripts[settings_hash] = CommandBlock() + script_fh.read()
            to_run.extend([settings_hash] * needed_repetitions)
            forecast_time += run_all.scripts[settings_hash].execution_time() * needed_repetitions
    if target_repetitions == 0 and max_count > 0:
        return run_all(max_count, dry_run, debug, recursion_limit)
    if not dry_run and len(to_run) > 0:
        random.shuffle(to_run)  # the order becomes unpredictable: I think it's a good idea
        for current, settings_hash in enumerate(to_run, start=1):
            script = run_all.scripts[settings_hash]
            print("Running {} ({}/{})...".format(settings_hash, current, len(to_run)))
            script.run(add_bash=settings_hash if debug else False)
        if recursion_limit <= 0:
            warnings.warn("Hit recursion limit. Some tests didn't run correctly!")
        else:
            run_all(target_repetitions, False, debug, recursion_limit - 1)
    return len(to_run), forecast_time, target_repetitions


def get_results_db(clear_cache=False, skip=[]):
    cache_file = 'cache/results.pdl'
    db = Base(cache_file)

    if clear_cache or not db.exists() or os.path.getmtime(cache_file) < os.path.getmtime(results_dir):
        warnings.warn('Rebuilding results cache...')
        columns = set()
        rows = []
        p = pathlib.Path(results_dir)
        for config_file in p.glob('*.config'):
            with config_file.open() as config_fh:
                settings_hash = config_file.stem
                row = json.loads(config_fh.read())
            if settings_hash in skip:
                continue
            row['hash'] = settings_hash
            tests_count = analyze.count(config_file.parent, settings_hash)
            row['iostat_cpu'], len_cpu_values = analyze.iostat_cpu(config_file.parent, settings_hash)
            row['iperf_result'], len_iperf_values = getattr(analyze, row['iperf_name'])(config_file.parent, settings_hash, row)
            if tests_count != len_cpu_values or tests_count != len_iperf_values:
                raise analyze.AnalysisException('For test {}, mismatch in cardinality of tests between count ({}), iostat ({}) and iperf ({})'.format(settings_hash, tests_count, len_cpu_values, len_iperf_values), settings_hash)
            if len_iperf_values > 0:
                min_fairness = row['iperf_result']['fairness'][0] - row['iperf_result']['fairness'][1]
                if min_fairness < (1 - 1 / (2 * row['parallelism'])):
                    warnings.warn('For test {}, fairness has a critical value: {}.'.format(settings_hash, row['iperf_result']['fairness']), RuntimeWarning)
            columns = columns | set(row.keys())
            rows.append(row)

        db.create(*columns, mode='override')
        for r in rows:
            db.insert(**r)
        db.commit()
        warnings.warn('Results cache built.')
    else:
        warnings.warn('Reusing results cache.')
        db.open()

    return db
