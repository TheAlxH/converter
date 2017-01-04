from InputReader import InputReader
from ..domains.contiguous.contiguous_domain import ContiguousDomain
from ..vendor.mps_parser import Parser as MPSParser


class MPSReader(InputReader):
    INF = float('inf')

    def __init__(self, **options):
        super(MPSReader, self).__init__(**options)

        self.mps_parser = MPSParser()
        self.mps_parser.convert_float = 'convert_float' in options
        self.var_table = {}

        self.options = options

    def parse(self, input_file, **kwargs):
        is_gzip = (input_file[-2:] == 'gz') if type(input_file) == str else False

        self.mps_parser.parse_mps(input_file, is_gzip)
        self.mps_parser.set_bounds()
        self.mps_parser.sort_vars()

        # weights, profits, capacity, instance_name = self.parse_one_instance(input_file)
        self.define_variables(self.mps_parser.vars, self.mps_parser.lo, self.mps_parser.up, self.mps_parser.freeLo)
        self.get_constraints(self.mps_parser.cond, self.mps_parser.rel, self.mps_parser.rhs)
        self.get_optimization_vector(self.mps_parser.opt.values()[0])
        self.converter.set_instance_name(self.mps_parser.name)

    def define_variables(self, variables, lower_bounds, upper_bounds, free_bounds):
        for var in variables:
            if var in lower_bounds:
                lb = lower_bounds[var]
            else:
                lb = 0

            if var in upper_bounds:
                ub = int(upper_bounds[var])
            else:
                ub = self.INF if 'ub' not in self.options else self.options['ub']
                if ub == self.INF:
                    self.converter.set_inf_bounds()

            self.var_table[var] = self.converter.new_int_variable(ContiguousDomain(lb, ub))

    def get_constraints(self, constraints, relations, b_vector):
        for constraint_id, weighted_vars in constraints.iteritems():
            if relations[constraint_id] == 'G':
                constraint = [(self.var_table[v], w) for v, w in constraints[constraint_id].iteritems()]
                b_value = 0 if constraint_id not in b_vector else b_vector[constraint_id]
                self.converter.add_ge_constraint(constraint, b_value)
            elif relations[constraint_id] == 'L':
                constraint = [(self.var_table[v], w) for v, w in constraints[constraint_id].iteritems()]
                # use 0 as default value if no value is given (according to the MPS specs)
                b_value = 0 if constraint_id not in b_vector else b_vector[constraint_id]
                self.converter.add_le_constraint(constraint, b_value)
            elif relations[constraint_id] == 'E':
                constraint = [(self.var_table[v], w) for v, w in constraints[constraint_id].iteritems()]
                b_value = 0 if constraint_id not in b_vector else b_vector[constraint_id]
                self.converter.add_eq_constraint(constraint, b_value)
            else:
                raise Exception('undefined constraint relation: ' + relations[constraint_id])

    def get_optimization_vector(self, weighted_vars):
        for var, weight in weighted_vars.iteritems():
            self.converter.add_to_opt_vector(self.var_table[var], weight)
