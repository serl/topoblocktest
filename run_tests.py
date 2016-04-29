#!/usr/bin/env python

from lib.test_master import run_all

if __name__ == '__main__':
    import argparse
    import argcomplete
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('target_repetitions', type=int, default=1, help='ensure all tests ran at least TARGET_REPETITIONS times')
    parser.add_argument('--dry-run', action='store_true', help='do not actually run the tests, only count them')
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    run_tests = run_all(args.target_repetitions, args.dry_run)
    if run_tests > 0:
        if args.dry_run:
            print("{} tests to be run.".format(run_tests))
    else:
        print("All tests ran already at least {} times.".format(args.target_repetitions))
