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


def run_all(target_repetitions=0, dry_run=False):
    to_run = []  # each script will appear N times, so to reach the target_repetitions
    p = pathlib.Path(results_dir)
    for script_file in p.glob('*.sh'):
        count = 0
        try:
            with script_file.parent.joinpath(script_file.stem + '.count').open() as count_fh:
                count = int(count_fh.read())
        except (FileNotFoundError, ValueError):
            pass
        to_run.extend([script_file] * (target_repetitions - count))
    if not dry_run:
        random.shuffle(to_run)  # the order becomes unpredictable, because I think it's a good idea
        for current, script_file in enumerate(to_run, start=1):
            with script_file.open() as script_fh:
                script = CommandBlock() + script_fh.read()
                print("Running {} ({}/{})...".format(script_file.name, current, len(to_run)))
                script.run()
    return len(to_run)


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
            row['iostat_cpu'], len_cpu_values = analyze.iostat_cpu(config_file.parent, settings_hash)
            row['iperf_result'], len_iperf_values = getattr(analyze, row['iperf_name'])(config_file.parent, settings_hash, row)
            if len_cpu_values != len_iperf_values:
                raise analyze.AnalysisException('For test {}, mismatch in cardinality of tests between iostat ({}) and iperf ({})'.format(settings_hash, len_cpu_values, len_iperf_values), settings_hash)
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
