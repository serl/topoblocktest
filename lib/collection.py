import lib.test_master as test_master
import lib.analyze as analyze
from lib import plot


class Collection:
    constants = {}
    variables = {}
    x_axis = None  # key on result dict
    x_title = None
    row_key_attributes = tuple()

    def __init__(self):
        if not len(self.constants) or not len(self.variables):
            raise ValueError('One attribute between `constants` and `variables` is required.')

    def generation_skip_fn(self, settings):
        return False

    def analysis_row_label_fn(self, row_element):
        raise ValueError('For analysis purposes, the `analysis_row_label_fn` must be redefined in subclass.')

    def analysis_row_key_fn(self, row_element):
        if not len(self.row_key_attributes):
            raise ValueError('For analysis purposes, the `row_key_attributes` is required.')
        raise Exception('TODO: implementation')

    def analysis_row_info_fn(self, row_element):
        return self.analysis_row_key_fn(row_element), self.analysis_row_label_fn(row_element),

    def analysis_grouping_fn(self, row_element):
        return (0,)

    def plot_style_fn(self, row_element, group_id):
        return {}  # matplotlib kwargs for the serie

    def generate(self):
        return test_master.generate_combinations(self.constants, self.variables, self.generation_skip_fn)

    def __analyze(self):
        if self.x_axis is None:
            raise ValueError('For analysis purposes, the `x_axis` attribute is required.')

        db = test_master.get_results_db()
        db_query = db
        for key, value in self.constants.items():
            db_query = [r for r in db_query if r[key] == value]
        for key, values in self.variables.items():
            db_query = [r for r in db_query if r[key] in values]
        return analyze.get_analysis_table(db_query, self.x_axis, self.analysis_row_info_fn, self.analysis_grouping_fn)

    def csv(self):
        cols, rows, rows_grouped = self.__analyze()
        data_header = 'label,' + ',,'.join(map(str, cols)) + ','
        throughput_values = ''
        cpu_values = ''
        fairness_values = ''
        for label, rowdetails in rows.items():
            values = rowdetails['row']
            throughput_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v['iperf_result']['throughput'])) if v is not None else ',' for v in values]))
            cpu_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v['iostat_cpu']['idle'])) if v is not None else ',' for v in values]))
            fairness_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, v['iperf_result']['fairness'] if 'fairness' in v['iperf_result'] else '')) if v is not None else ',' for v in values]))
        print('throughput')
        print(data_header)
        print(throughput_values)
        print('cpu idle')
        print(data_header)
        print(cpu_values)
        print('fairness')
        print(data_header)
        print(fairness_values)

    def plot(self):
        cols, rows, rows_grouped = self.__analyze()
        plot.throughput_cpu(cols, rows_grouped, self.x_title, self.plot_style_fn)

    def parse_shell_arguments(self):
        import argparse
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('action', choices=('generate', 'csv', 'plot'), help='action to take')
        args = parser.parse_args()
        getattr(self, args.action)()
