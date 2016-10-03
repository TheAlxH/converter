import sys
from OutputWriter import OutputWriter
from .. import ILPParser
from ..domains.continuous.continuous_domain import ContinuousDomain


class AspartameWriter(OutputWriter):
    INF = float('inf')

    def __init__(self, **options):
        super(AspartameWriter, self).__init__(**options)
        self.constraint_id = 1

    def write(self, output_filename, variables_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        if not output_filename:
            raise Exception('no output filename specified')

        self.output_file = open(output_filename + '.lp', 'w') if output_filename != sys.stdout else sys.stdout

        self.output_file.write('%%% ' + self.parser.instance_name + ' %%%\n\n')

        self.write_bool_variable(bool_vars, len(b2i) * 2)
        self.write_bounds(variables_with_bounds, opt_vector)
        self.write_clauses(clauses)
        self.write_constraints(constraints)
        self.write_bool_to_int(b2i)

        self.write_objective_fn(opt_vector)
        self.output_file.write('\n')

    def write_bool_variable(self, b_vars, helper_vars):
        if b_vars or helper_vars > 0:
            self.output_file.write('% BOOLEANS\n')

            for var in b_vars:
                self.output_file.write('var(bool, "%s").\n' % var)

            for i in xrange(helper_vars):
                self.output_file.write('var(bool, "$B%d").\n' % (i + 1))

            self.output_file.write('\n')

    # TODO handle non-continuous domains
    def write_bounds(self, domains, opt_vector):
        self.output_file.write('% BOUNDS\n')

        for var in sorted(domains.iterkeys(), key=ILPParser.ILPParser.cmp_vars):
            lb, ub = domains[var].lb(), domains[var].ub()
            ub = 'inf' if ub == AspartameWriter.INF else str(ub)

            try:
                self.output_file.write('var(int, "%s", (range(%i, %s))).\n' % (var, lb, ub))
            except TypeError:
                sys.stderr.write('Error: infinity bounds not supported\n')
                sys.stderr.write('Error: translation canceled\n')
                sys.exit(1)

        if opt_vector:
            self.write_objective_dom(domains, opt_vector)

    def write_objective_dom(self, bounds, opt_vector):
        lb = ub = 0
        n_dom = 1

        for var, w in opt_vector:
            n_dom *= bounds[var].len()
            if w < 0:
                lb += w * bounds[var].ub()
                ub += w * bounds[var].lb()
            else:
                lb += w * bounds[var].lb()
                ub += w * bounds[var].ub()

        if len(opt_vector) == 1:
            var, w = opt_vector[0]
            self._write_domain('opt', bounds[var].copy(multiplier=w))
        if n_dom <= 10000:
            var, w = opt_vector[0]
            dom = bounds[var].copy(multiplier=w)
            for var, w in opt_vector[1:]:
                d = bounds[var].copy(multiplier=w)
                dom = ILPParser.ILPParser.merge_dom(dom, d)
            self._write_domain('opt', dom)
        else:
            self._write_domain('opt', ContinuousDomain(lb, ub))

    def write_clauses(self, clauses):
        if clauses:
            self.output_file.write('\n% CLAUSES\n')

            for clause in clauses:
                literals = '; '.join(map(AspartameWriter._format_literal, clause))
                self.output_file.write('constraint(%d, (%s)).\n' % (self.constraint_id, literals))
                self.constraint_id += 1

    @staticmethod
    def _format_literal(literal):
        if literal[0] == '-':
            return 'op(neg, "%s")' % literal[1:]
        else:
            return '"' + literal + '"'

    def write_constraints(self, constraints):
        self.output_file.write("\n% CONDITIONS\n")

        rel = "ge"

        for var_list, b, r in constraints:
            if r is not None:
                sys.stderr.write("Error: SugarWriter has no support for reified constraints implemented.\n")
                sys.exit(1)
            wsum = self.get_weighted_sum(var_list)

            self.output_file.write('constraint(%i, (op(%s, %s, %i))).\n' % (self.constraint_id, rel, wsum, b))

            self.constraint_id += 1

    def write_bool_to_int(self, b2i):
        if b2i:
            b2i_counter = 1
            self.output_file.write('\n% BOOL TO INT')

            c1 = 'constraint(%d,("$B%d";"$B%d")).\n'
            c2 = 'constraint(%d,("%s";op(neg,"$B%d"))).\n'
            c3 = 'constraint(%d,(op(le,op(mul,1,"%s"),1);op(neg,"$B%d"))).\n'
            c4 = 'constraint(%d,(op(ge,op(mul,1,"%s"),1);op(neg,"$B%d"))).\n'
            c5 = 'constraint(%d,(op(neg,"%s");op(neg,"$B%d"))).\n'
            c6 = 'constraint(%d,(op(le,op(mul,1,"%s"),0);op(neg,"$B%d"))).\n'

            for b, i in b2i:
                self.output_file.write('\n%% b2i(%s, %s)\n' % (b, i))
                self.output_file.write(c1 % (self.constraint_id, b2i_counter, b2i_counter + 1))
                self.output_file.write(c2 % (self.constraint_id + 1, b, b2i_counter))
                self.output_file.write(c3 % (self.constraint_id + 2, i, b2i_counter))
                self.output_file.write(c4 % (self.constraint_id + 3, i, b2i_counter))
                self.output_file.write(c5 % (self.constraint_id + 4, b, b2i_counter + 1))
                self.output_file.write(c6 % (self.constraint_id + 5, i, b2i_counter + 1))

                self.constraint_id += 6
                b2i_counter += 2

    @staticmethod
    def get_weighted_sum(var_list):

        op1 = AspartameWriter.create_multiplication(var_list[0])

        for i in xrange(1, len(var_list)):
            op2 = AspartameWriter.create_multiplication(var_list[i])
            op1 = AspartameWriter.create_sum(op1, op2)

        return op1

    @staticmethod
    def create_multiplication(parts):
        var, weight = parts
        return 'op(mul, %i, "%s")' % (weight, var)

    @staticmethod
    def create_sum(arg1, arg2):
        return 'op(add, %s, %s)' % (arg1, arg2)

    def write_objective_fn(self, opt_vector):
        if opt_vector:
            opt_sum = AspartameWriter.get_weighted_sum(opt_vector + [('opt', -1)])
            self.output_file.write('\n% OPTIMIZATION\n')
            self.output_file.write('constraint(%i, (op(ge, %s, 0))).\n' % (self.constraint_id, opt_sum))
            self.output_file.write('constraint(%i, (op(le, %s, 0))).\n' % (self.constraint_id + 1, opt_sum))
            self.output_file.write('objective(minimize, "opt").\n')
            self.constraint_id += 2

    def _write_domain(self, var, domain):
        if isinstance(domain, ContinuousDomain) and abs(domain.multiplier) == 1:
            self.output_file.write('var(int, "%s", (range(%d, %d))).\n' % (var, domain.lb(), domain.ub()))
        else:
            for d in domain.get_values_asc():
                self.output_file.write('var(int, "{0}", (range({1}, {1}))).\n'.format(var, d))
