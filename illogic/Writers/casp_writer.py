import sys
from OutputWriter import OutputWriter
from .. import ILPParser
from ..domains.contiguous.contiguous_domain import ContiguousDomain


class CASPWriter(OutputWriter):
    INF = float('inf')

    def __init__(self, **options):
        super(CASPWriter, self).__init__(**options)
        self.clause_counter = 1

    def write(self, output_filename, variables_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        if not output_filename:
            raise Exception('no output filename specified')

        self.output_file = file(output_filename + '.lp', 'w') if output_filename != sys.stdout else sys.stdout

        if type(self.converter.instance_name) == str:
            self.output_file.write('%%% ' + self.converter.instance_name + ' %%%\n')

        if 'csp' not in self.options or self.options['csp']:
            csp_path = self.options['csp'] if 'csp' in self.options else 'csp.lp'
            self.output_file.write("#include \"%s\".\n\n" % csp_path)

        if self.converter.has_inf_bounds():
            self.output_file.write('has_inf_dom.\n\n')

        self.write_domains(variables_with_bounds, bool_vars)
        self.write_clauses(clauses)
        self.write_constraints(constraints)
        self.write_b2i(b2i)

        self.write_objective_fn(opt_vector)
        self.write_show(variables_with_bounds)
        self.output_file.write('\n')

    # TODO handle non-contiguous domains
    def write_domains(self, bounds, booleans):
        if booleans:
            self.output_file.write('% BOOLS\n')
            for b in booleans:
                self.write_bool_variable(b)
            self.output_file.write('{ p(B) : bool(B) }.\n\n')

        self.output_file.write('% DOMAINS\n')

        for var in sorted(bounds.iterkeys(), key=ILPParser.ILPParser.cmp_vars):
            dom = bounds[var]
            lb, ub = dom.lb(), dom.ub()

            if (not isinstance(dom, ContiguousDomain) or abs(
                    dom.multiplier) > 1) and not dom.has_open_bound() or dom.len() == 1:
                values = map(str, dom.get_values_asc())
                self.output_file.write('&dom{ %s } = %s.\n' % ('; '.join(values), var))
            else:
                ub = 'inf' if ub == CASPWriter.INF else str(ub)

                try:
                    self.output_file.write('&dom{ %d .. %s } = %s.\n' % (lb, ub, var))
                except TypeError:
                    sys.stderr.write('ERROR: infinity bounds not supported\n')
                    sys.stderr.write('ERROR: translation canceled\n')
                    sys.exit(1)

    def write_bool_variable(self, var):
        self.output_file.write('bool("%s").\n' % var)

    def write_clauses(self, clauses):
        if clauses:
            self.output_file.write('\n% CLAUSES.\n')

            for clause in clauses:
                for lit in clause:
                    if lit[0] == '-':
                        signed = 1
                        lit = lit[1:]
                    else:
                        signed = 0
                    self.output_file.write('clause(%d, "%s", %d).\n' % (self.clause_counter, lit, signed))
                self.clause_counter += 1

            self.output_file.write('clause(ID) :- clause(ID, _, _).\n')
            self.output_file.write(':- clause(ID), p(B0) : clause(ID, B0, 1); not p(B1) : clause(ID, B1, 0).\n')

    def write_constraints(self, constraints):
        self.output_file.write("\n% CONSTRAINTS\n")

        for var_list, b, rel in constraints:
            w_sum = self.get_weighted_sum(var_list)

            self.output_file.write('&sum{ %s } >= %d.\n' % ("; ".join(w_sum), b))

    def write_b2i(self, b2i):
        if b2i:
            self.output_file.write('\n% BOOL TO INT\n')
            for c in b2i:
                self.output_file.write('b2i("%s", %s).\n' % c)
            self.output_file.write(':- b2i(B, X), p(B), not p(X, 1).\n')
            self.output_file.write(':- b2i(B, X), not p(B), p(X, 1).\n')

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

    def write_show(self, variables):
        if "no-show" not in self.options or self.options["no-show"] is False:
            self.output_file.write('\n&show{ %s }.\n' % "; ".join(variables.keys()))
            self.output_file.write('#show p/1.\n\n')
        else:
            self.output_file.write('\n#show.\n')
