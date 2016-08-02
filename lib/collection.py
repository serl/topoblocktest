import lib.test_master as test_master
import lib.analyze as analyze
from lib import plot


class Collection:
    constants = {}
    variables = {}
    x_axis = None  # key on result dict
    x_limits = None  # tuple (min, max)
    y_axes = []  # strings or YAx subclasses (see `plot` module)
    x_title = None
    filters = {}  # name => skip_fn
    plot_legend_loc = 1

    def __init__(self):
        self.__custom_filters = []
        self.reference = {}
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

    def analyze(self):
        if self.x_axis is None:
            raise ValueError('For analysis purposes, the `x_axis` attribute is required.')

        db = test_master.get_results_db()
        self.__db_query = db
        for key, value in self.constants.items():
            self.__db_query = [r for r in self.__db_query if r[key] == value]
        for key, values in self.variables.items():
            self.__db_query = [r for r in self.__db_query if r[key] in values]
        self.__db_query = [r for r in self.__db_query if not self.generation_skip_fn(r)]
        analysis_query = self.__db_query
        for fil in self.__custom_filters:
            analysis_query = [r for r in analysis_query if not fil(r)]
        return analyze.get_analysis_table(analysis_query, self.x_axis, self.analysis_row_info_fn, self.analysis_grouping_fn)

    def is_relative(self):
        return len(self.reference) > 0

    def get_reference_row(self, r):
        remove_keys = ('__id__', '__version__', 'hash', 'iperf_result', 'iostat_cpu')
        query = self.__db_query
        for key in r.keys():
            if key in remove_keys or r[key] is None:
                continue
            value = r[key]
            if key in self.reference:
                value = self.reference[key]
            query = [r for r in query if r[key] == value]
        if len(query) > 1:
            raise ValueError('Something bad happened :(')
        if len(query) == 0:
            return None
        return query[0]

    def csv(self):
        cols, rows, rows_grouped = self.analyze()
        data_header = 'label,' + ',,'.join(map(str, cols)) + ','
        throughput_values = ''
        cpu_values = ''
        iowait_values = ''
        fairness_values = ''

        def get_valuerr(y_ax, r):
            if y_ax == 'throughput':
                return r['iperf_result']['throughput']
            elif y_ax == 'cpu':
                return r['iostat_cpu']['idle']
            elif y_ax == 'iowait':
                return r['iostat_cpu']['iowait']
            elif y_ax == 'fairness':
                return r['iperf_result']['fairness'] if 'fairness' in r['iperf_result'] else ''

        if self.is_relative():
            _under_get_valuerr = get_valuerr

            def get_valuerr(y_ax, r):
                ref_r = self.get_reference_row(r)
                value_error = _under_get_valuerr(y_ax, r)
                ref_value_error = _under_get_valuerr(y_ax, ref_r)
                return ((value_error[0] - ref_value_error[0]) * 100 / ref_value_error[0], (value_error[1] + ref_value_error[1]) * 100 / ref_value_error[0])

        for label, rowdetails in rows.items():
            values = rowdetails['row']
            throughput_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, get_valuerr('throughput', v))) if v is not None else ',' for v in values]))
            cpu_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, get_valuerr('cpu', v))) if v is not None else ',' for v in values]))
            iowait_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, get_valuerr('iowait', v))) if v is not None else ',' for v in values]))
            fairness_values += '"{}",{}\n'.format(label, ','.join([','.join(map(str, get_valuerr('fairness', v))) if v is not None else ',' for v in values]))

        print('throughput')
        print(data_header)
        print(throughput_values)
        print('cpu idle')
        print(data_header)
        print(cpu_values)
        print('cpu iowait')
        print(data_header)
        print(iowait_values)
        print('fairness')
        print(data_header)
        print(fairness_values)

    def plot(self, export=None):
        plot.dynamic(self, export)

    def plot_hook(self, ax, row_id, y_ax, x_values, y_values, y_error, style):
        return True

    def is_filter_selected(self, filter_name):
        return self.filters[filter_name] in self.__custom_filters

    def parse_shell_arguments(self):
        import argparse
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('action', choices=('generate', 'csv', 'plot'), default='plot', nargs='?', help='action to take')
        parser.add_argument('--out', help='redirect the output to file')
        if len(self.filters) > 0:
            parser.add_argument('--filter', choices=self.filters.keys(), nargs='+', help='use a predefined filter to read less data (depends on the collection). Does not work for `generate`.')
        parser.add_argument('--plot-y-axes', nargs='+', help='specify optionally which y-axes you want on the figure.')
        parser.add_argument('--plot-legend-loc', help='specify optionally the loc parameter for matplotlib legend.')
        parser.add_argument('--plot-hook', action='store_true', help='extend/replace the plot functionality with the custom code in the Collection implementation (if present).')
        parser.add_argument('--relative-to', nargs='+', metavar='attribute=value', help='output relative values instead of absolute. Must specify values in the form "attribute=value", for example "parallelism=1".')
        args = parser.parse_args()

        if hasattr(args, 'filter') and args.filter is not None:
            for filtername in args.filter:
                self.__custom_filters.append(self.filters[filtername])

        if args.relative_to is not None:
            for ref in args.relative_to:
                # check the form
                try:
                    attr_name, attr_value = ref.split('=', 1)
                except ValueError:
                    raise ValueError("is '{}' in the form attribute=value?".format(ref))

                # check the existence of the attribute
                if attr_name not in self.variables:
                    raise ValueError("'{}' is not in the 'variables', using it as a reference would have no useful effects".format(attr_name))

                # check the value, cast if necessary
                found = False
                for good_value in self.variables[attr_name]:
                    casted_value = attr_value
                    if type(good_value) == type(1):
                        casted_value = int(attr_value)
                    elif type(good_value) == type(1.0):
                        casted_value = float(attr_value)
                    elif type(good_value) == type(True):
                        if attr_value == 'True':
                            casted_value = True
                        elif attr_value == 'False':
                            casted_value = False
                        else:
                            raise ValueError("could not convert string to bool: '{}'".format(attr_value))
                    found = (casted_value == good_value)
                    if found:
                        attr_value = casted_value
                        break
                if not found:
                    raise ValueError('"{}" is not an acceptable value for "{}". Good values are: {}.'.format(attr_value, attr_name, self.variables[attr_name]))

                self.reference[attr_name] = attr_value

        if args.plot_y_axes is not None:
            self.y_axes = args.plot_y_axes
        if args.plot_legend_loc is not None:
            self.plot_legend_loc = args.plot_legend_loc
        self.plot_hook_enabled = args.plot_hook

        action_kwargs = {}
        if args.out is not None:
            action_kwargs['export'] = args.out

        getattr(self, args.action)(**action_kwargs)
