import sys
from OutputWriter import OutputWriter
from .. import ILPParser
from ..domains.continuous.continuous_domain import ContinuousDomain


class CASPWriter(OutputWriter):
    INF = float('inf')

    def write(self, output_filename, variables_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        if not output_filename:
            raise Exception('no output filename specified')

        self.output_file = file(output_filename + '.lp', 'w') if output_filename != sys.stdout else sys.stdout

        if type(self.parser.instance_name) == str:
            self.output_file.write('%%% ' + self.parser.instance_name + ' %%%\n')
        self.output_file.write("#include \"csp.lp\".\n\n")

        if self.parser.has_inf_bounds():
            self.output_file.write('has_inf_dom.\n\n')

        # FIXME workaround for bool vars: (convert into int)
        variables_with_bounds.update({'b' + var: ContinuousDomain(0, 1) for var in bool_vars})

        self.write_domains(variables_with_bounds)
        self.write_constraints(constraints)

        self.write_objective_fn(opt_vector)
        self.output_file.write('\n')

        # self.output_file.close()

    # TODO handle non-continuous domains
    def write_domains(self, bounds):
        self.output_file.write('% DOMAINS\n')

        for var in sorted(bounds.iterkeys(), key=ILPParser.ILPParser.cmp_vars):
            lb, ub = bounds[var].lb(), bounds[var].ub()

            if lb == 0 and ub == 1:
                self.write_bool_variable(var)
            else:
                ub = 'inf' if ub == CASPWriter.INF else str(ub)

                try:
                    if str(lb) != str(ub):
                        self.output_file.write('&dom{ %d..%s } = %s.\n' % (lb, ub, var))
                    else:
                        self.output_file.write('&dom{ %d } = %s.\n' % (lb, var))
                except TypeError:
                    sys.stderr.write('infinity bounds not supported\n')
                    sys.stderr.write('translation canceled\n')
                    sys.exit(1)

    def write_bool_variable(self, var):
        self.output_file.write('&dom{ 0; 1 } = %s.\n' % var)

    def write_constraints(self, constraints):
        self.output_file.write("\n% CONDITIONS\n")

        for var_list, b, rel in constraints:
            w_sum = self.get_weighted_sum(var_list)

            self.output_file.write('&sum{ %s } %s %d.\n' % ("; ".join(w_sum), ">=" if rel == "ge" else "<=", b))

    @staticmethod
    def get_weighted_sum(var_list):
        return map(CASPWriter.create_multiplication, var_list)

    @staticmethod
    def create_multiplication(part):
        return "%d * %s" % part[::-1]

    @staticmethod
    def create_sum(arg1, arg2):
        return 'op(add, %s, %s)' % (arg1, arg2)

    def write_objective_fn(self, opt_vector):
        if len(opt_vector):
            terms = ["%d * %s" % (w, x) for x, w in opt_vector]
            opt_term = "; ".join(terms)

            self.output_file.write("\n&minimize{ %s }." % opt_term)
