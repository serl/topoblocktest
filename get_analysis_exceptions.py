from lib.test_master import get_results_db
from lib.analyze import AnalysisException


def count_exceptions():
    count = 0
    skip = []
    exceptions_found = True
    while exceptions_found:
        try:
            exceptions_found = False
            db = get_results_db(True, skip=skip)
        except AnalysisException as e:
            exceptions_found = True
            print('Exception: {}'.format(e))
            skip.append(e.test_hash)
            count += 1
    print("{} total exceptions.".format(count))

if __name__ == '__main__':
    count_exceptions()
