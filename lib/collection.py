import lib.test_master as test_master
import lib.analyze as analyze
from lib import plot


class Collection:
    constants = {}
    variables = {}
    x_axis = None  # key on result dict
    y_axes = []  # strings or YAx subclasses (see `plot` module)
    x_title = None
    filters = {}  # name => skip_fn

    def __init__(self):
        self.__custom_filters = []
        if not len(self.constants) or not len(self.variables):
            raise ValueError('One attribute between `constants` and `variables` is required.')

    def generation_skip_fn(self, settings):
        return False

    def analysis_row_label_fn(self, row_element):
        raise ValueError('For analysis purposes, the `analysis_row_label_fn` must be defined in subclass.')

    def analysis_row_key_fn(self, row_element):
        key = ''
        for attr_name, attr_values in self.variables.items():
            if attr_name == self.x_axis:
                continue
            value = row_element[attr_name]
            if attr_name == 'packet_size' and value == 'default':
                value = '0'
            attr_values_max_len = max(map(len, map(str, attr_values)))
            key += "{0:>{1}}".format(value, attr_values_max_len)
        return key

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
        for fil in self.__custom_filters:
            db_query = [r for r in db_query if not fil(r)]
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
        plot.dynamic(cols, rows_grouped, self.y_axes, self.x_title, self.__class__.__name__, self.plot_style_fn)

    def parse_shell_arguments(self):
        import argparse
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('action', choices=('generate', 'csv', 'plot'), default='plot', nargs='?', help='action to take')
        if len(self.filters) > 0:
            parser.add_argument('--filter', choices=self.filters.keys(), nargs='+', help='use a predefined filter to read less data (depends on the collection). Does not work for `generate`.')
        args = parser.parse_args()
        if hasattr(args, 'filter') and args.filter is not None:
            for filtername in args.filter:
                self.__custom_filters.append(self.filters[filtername])
        getattr(self, args.action)()
