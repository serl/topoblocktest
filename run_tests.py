from lib.test_master import run_all

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('target_repetitions', type=int, default=1, help='ensure all tests ran at least TARGET_REPETITIONS times')
    args = parser.parse_args()
    run_all(args.target_repetitions)