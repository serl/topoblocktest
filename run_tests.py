from lib.test_master import run_all

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('target_repetitions', type=int, default=1, help='ensure all tests ran at least TARGET_REPETITIONS times')
    args = parser.parse_args()
    if run_all(args.target_repetitions) > 0:
        print("Beware, in case of errors, the tests are not automatically relaunched. So rerun this command to be sure ;)")
    else:
        print("All tests ran already at least {} times.".format(args.target_repetitions))
