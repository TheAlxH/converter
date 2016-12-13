import sys
from OutputWriter import OutputWriter
from .. import ILPParser
from ..domains.contiguous.contiguous_domain import ContiguousDomain


class SugarWriter(OutputWriter):
    def write(self, output_filename, variables_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        if not output_filename:
            raise Exception('no output filename specified')

        self.output_file = file(output_filename + '.csp', 'w') if output_filename != sys.stdout else sys.stdout

        self.write_bool_vars(bool_vars)
        self.write_bounds(variables_with_bounds, opt_vector)
        self.write_clauses(clauses)
        self.write_constraints(constraints)
        self.write_bool_to_int(b2i)

        self.write_objective_fn(opt_vector)

        self.output_file.close()

    def write_bool_vars(self, variables):
        if len(variables) > 0:
            self.output_file.write(';; BOOLEANS\n')

            for var in variables:
                self.output_file.write('(bool b%s)\n' % var)

            self.output_file.write('\n')

    def write_bounds(self, bounds, opt_vector):
        self.output_file.write(';; BOUNDS\n')

        for var in sorted(bounds.iterkeys(), key=ILPParser.ILPParser.cmp_vars):
            try:
                self._write_domain(var, bounds[var])
            except TypeError:
                sys.stderr.write('Error: infinity bounds not supported\n')
                sys.stderr.write('Error: translation canceled\n')
                sys.exit(1)

        # create new opt variable
        if opt_vector:
            self.write_objective_dom(bounds, opt_vector)

    def write_clauses(self, clauses):
        if len(clauses):
            self.output_file.write("\n;; CLAUSES\n")

            for clause in clauses:
                self.output_file.write('(or %s)\n' % ' '.join(map(SugarWriter._format_literal, clause)))

    @staticmethod
    def _format_literal(literal):
        if literal[0] == '-':
            return '(not b%s)' % literal[1:]
        else:
            return 'b' + literal

    def write_constraints(self, constraints):
        self.output_file.write("\n;; CONDITIONS\n")

        rel = ">="

        for var_list, b, r in constraints:
            if r is not None:
                sys.stderr.write("Error: SugarWriter has no support for reified constraints implemented.\n")
                sys.exit(1)
            add_list = []
            for var, w in var_list:
                add_list.append('(* %d %s)' % (w, var))

            self.output_file.write('(%s (+ %s) %d)\n' % (rel, ' '.join(add_list), b))

    def write_bool_to_int(self, b2i):
        if len(b2i):
            self.output_file.write('\n;; BOOL TO INT\n')

            for b, i in b2i:
                self.output_file.write('(or (and b{b} (eq {i} 1)) (and (not b{b}) (eq {i} 0)))\n'.format(b=b, i=i))

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
            self._write_domain('opt', ContiguousDomain(lb, ub))

    def write_objective_fn(self, opt_vector):
        if len(opt_vector) > 0:
            w_sum = ' '.join(map(lambda (var, w): '(%d %s)' % (w, var), opt_vector))
            self.output_file.write('\n;; OPTIMIZATION\n')
            self.output_file.write('(weightedsum (%s) eq opt)\n' % w_sum)
            self.output_file.write('(objective minimize opt)\n')

    def _write_domain(self, var, domain):
        if isinstance(domain, ContiguousDomain) and abs(domain.multiplier) == 1:
            self.output_file.write('(int %s %d %d)\n' % (var, domain.lb(), domain.ub()))
        else:
            self.output_file.write('(int %s (%s))\n' % (var, ' '.join(map(lambda x: '%s' % x, list(domain.get_values())))))
