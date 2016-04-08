import re
import os
import pathlib
import json
import hashlib
import random
import itertools
import lib.topologies as topologies
import lib.tests as tests
from lib.bash import CommandBlock

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


def run_all(target_repetitions=0):
    to_run = []  # each script will appear N times, so to reach the target_repetitions
    p = pathlib.Path(results_dir)
    for script_file in p.glob('*.sh'):
        count = 0
        try:
            with script_file.parent.joinpath(script_file.stem + '.count').open() as count_fh:
                count = int(count_fh.read())
        except FileNotFoundError:
            pass
        to_run.extend([script_file] * (target_repetitions - count))
    random.shuffle(to_run)  # the order becomes unpredictable, because I think it's a good idea
    for current, script_file in enumerate(to_run, start=1):
        with script_file.open() as script_fh:
            script = CommandBlock() + script_fh.read()
            print("Running {} ({}/{})...".format(script_file.name, current, len(to_run)))
            script.run()
