from .. import OutputWriter
from .. import ILPParser
import sys


class TinoWriter(OutputWriter.OutputWriter):
    def write(self, output_filename, variables_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        self.output_file = file(output_filename + '.lp', 'w') if output_filename != sys.stdout else sys.stdout

        self.write_opt_strategy()
        self.write_opt_vector(opt_vector)
        self.write_constraints(constraints)
        self.write_bounds(variables_with_bounds)

    def write_opt_strategy(self):
        self.output_file.write("minimization.\n\n")

    def write_opt_vector(self, opt_vector):
        """
        :type opt_vector: list
        """
        self.output_file.write("% Optimization: COST\n")

        for x, w in opt_vector:
            self.output_file.write("c(%s, %d). " % (x, w))

        self.output_file.write("\n\n")

    def write_constraints(self, constraints):
        """
        :type constraints: list
        """
        self.output_file.write("% Conditions\n")
        constraint_counter = 0

        for var_list, b, _ in constraints:
            constraint_counter += 1
            last_var = 'start'

            for var, w in var_list:
                self.output_file.write("order(%d, %s, (%d, %s)). " % (constraint_counter, last_var, w, var))
                last_var = var

            self.output_file.write("order(%d, %s, end).\n" % (constraint_counter, last_var))
            self.output_file.write("b(%d, %d).\n" % (constraint_counter, b))

        self.output_file.write("\n")

    def write_bounds(self, bounds):
        """
        :type bounds: dict
        """
        self.output_file.write("% Bounds\n")

        for bound in sorted(bounds.iterkeys(), key=ILPParser.ILPParser.cmp_vars):
            b = bounds[bound]

            self.output_file.write("l(%s, %s). u(%s, %s).\n" % (bound, b.lb(), bound, b.ub()))