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
    run_tests, forecast_time, target_repetitions = run_all(args.target_repetitions, args.dry_run)
    if run_tests > 0:
        if args.dry_run:
            hours, remainder = divmod(forecast_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_time = '{:.0f}h{:02.0f}m{:02.0f}s'.format(hours, minutes, seconds)
            print("{} tests to be run in order to hit {} repetitions for each experiment.\nThis should take no more than {}.".format(run_tests, target_repetitions, formatted_time))
    else:
        print("All tests ran already at least {} times.".format(target_repetitions))
