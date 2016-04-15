import lib.test_master
from lib.analyze import AnalysisException


def count_exceptions():
    count = 0
    skip = []
    exceptions_found = True
    while exceptions_found:
        try:
            exceptions_found = False
            db = lib.test_master.get_results_db(True, skip=skip)
        except AnalysisException as e:
            exceptions_found = True
            print('Exception: {}'.format(e))
            skip.append(e.test_hash)
            count += 1
    return skip

if __name__ == '__main__':
    import subprocess
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--run-editor', help='run the specified editor for each Exception')
    args = parser.parse_args()

    test_hashes = count_exceptions()
    print("{} total exceptions.".format(len(test_hashes)))
    if args.run_editor is not None:
        for test_hash in test_hashes:
            proc = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, universal_newlines=True)
            proc.communicate('{} {}{}.*'.format(args.run_editor, lib.test_master.results_dir, test_hash))
