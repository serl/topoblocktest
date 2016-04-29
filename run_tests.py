#!/usr/bin/env python

from lib.test_master import run_all

if __name__ == '__main__':
    import argparse
    import argcomplete
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('target_repetitions', type=int, default=0, nargs='?', help='ensure all tests ran at least TARGET_REPETITIONS times. If not present, it will be guessed by taking the most repeated test.')
    parser.add_argument('--dry-run', action='store_true', help='do not actually run the tests, only count them')
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    run_tests, target_repetitions = run_all(args.target_repetitions, args.dry_run)
    if run_tests > 0:
        if args.dry_run:
            print("{} tests to be run in order to hit {} repetitions for each experiment.".format(run_tests, target_repetitions))
    else:
        print("All tests ran already at least {} times.".format(target_repetitions))
