from InputReader import InputReader
from ..domains.continuous.continuous_domain import ContinuousDomain
from ..vendor.mps_parser import Parser as MPSParser


class MPSReader(InputReader):
    INF = float('inf')

    def __init__(self, convert_float=False):
        super(MPSReader, self).__init__()

        self.mps_parser = MPSParser()
        self.mps_parser.convert_float = convert_float
        self.var_table = {}

    def parse(self, input_file, **kwargs):
        is_gzip = (input_file[-2:] == 'gz') if type(input_file) == str else False

        self.mps_parser.parse_mps(input_file, is_gzip)
        self.mps_parser.set_bounds()
        self.mps_parser.sort_vars()

        # weights, profits, capacity, instance_name = self.parse_one_instance(input_file)
        self.define_variables(self.mps_parser.vars, self.mps_parser.lo, self.mps_parser.up, self.mps_parser.freeLo)
        self.get_constraints(self.mps_parser.cond, self.mps_parser.rel, self.mps_parser.rhs)
        self.get_optimization_vector(self.mps_parser.opt.values()[0])
        self.parser.set_instance_name(self.mps_parser.name)

    def define_variables(self, variables, lower_bounds, upper_bounds, free_bounds):
        for var in variables:
            # if var in free_bounds:
            #     raise Exception('lower bound values less than zero not allowed in ILP')

            if var in lower_bounds:
                lb = lower_bounds[var]
            else:
                lb = 0

            if var in upper_bounds:
                ub = int(upper_bounds[var])
            else:
                ub = self.INF
                self.parser.set_inf_bounds()

            # if lb < 0 or ub < 0:
            #     raise Exception('bound values less than zero not allowed in ILP')

            self.var_table[var] = self.parser.new_int_variable(ContinuousDomain(lb, ub))

    def get_constraints(self, constraints, relations, b_vector):
        for constraint_id, weighted_vars in constraints.iteritems():
            if relations[constraint_id] == 'G':
                constraint = [(self.var_table[v], w) for v, w in constraints[constraint_id].iteritems()]
                b_value = 0 if constraint_id not in b_vector else b_vector[constraint_id]
                self.parser.add_ge_constraint(constraint, b_value)
            elif relations[constraint_id] == 'L':
                constraint = [(self.var_table[v], w) for v, w in constraints[constraint_id].iteritems()]
                # use 0 as default value if no value is given (according to the MPS specs)
                b_value = 0 if constraint_id not in b_vector else b_vector[constraint_id]
                self.parser.add_le_constraint(constraint, b_value)
            elif relations[constraint_id] == 'E':
                constraint = [(self.var_table[v], w) for v, w in constraints[constraint_id].iteritems()]
                b_value = 0 if constraint_id not in b_vector else b_vector[constraint_id]
                self.parser.add_eq_constraint(constraint, b_value)
            else:
                raise Exception('undefined constraint relation: ' + relations[constraint_id])

    def get_optimization_vector(self, weighted_vars):
        # self.parser.set_opt_strategy("minimize" if self.mps_parser.minimize else "maximize")
        # self.parser.set_opt_strategy("maximize")

        for var, weight in weighted_vars.iteritems():
            self.parser.add_to_opt_vector(self.var_table[var], weight)
