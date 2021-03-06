import os.path
import sys
from datetime import datetime
from math import log10, ceil

from Readers import InputReader
from Writers import OutputWriter
from domains.contiguous.contiguous_domain import ContiguousDomain
from domains.domain import *
from domains.domain_by_enum import DomainByEnum
from domains.domain_by_monotonic_function import DomainByMonotonicFunction


class ILPParser:
    opt_strategies = [
        "minimize",
        "maximize"
    ]

    max_num_digests = 1

    def __init__(self, input_reader, output_writer, **options):
        if not isinstance(input_reader, InputReader.InputReader):
            raise Exception("input_reader must be an instance of InputReader")
        elif not isinstance(output_writer, OutputWriter.OutputWriter):
            raise Exception("output_writer must be an instance of OutputWriter")

        self.reader = input_reader
        self.writer = output_writer

        self.reader.set_converter(self)
        self.writer.set_converter(self)

        self.inf_dom = False

        self.opt_vector = []
        self.opt_strategy = 'minimize'
        self.constraint_matrix = []
        self.variables = {}
        self.bool_variables = {"1"}
        self.clauses = [["1"]]
        self.bool_to_int = []

        self.instance_name = ''

        self.options = options
        self.stats = {
            'constr_len': []
        }

    def parse_input(self, input_file, **kwargs):
        self.reset()
        r = self.reader.parse(input_file, **kwargs)
        if 'stats' in self.options and self.options['stats']:
            self.print_stats()
        return r

    def print_stats(self):
        max_digit = max(
            [len(self.variables.keys()), len(self.bool_variables), len(self.constraint_matrix), len(self.clauses)])
        max_digit = str(len(str(max_digit)))

        sys.stderr.write('int variables:           %~d\n'.replace('~', max_digit) % len(self.variables.keys()))
        if not self.inf_dom:
            avg, median = self.avg_domain_len()
            sys.stderr.write('  avg domain size:       %~.2f\n'.replace('~', max_digit) % avg)
            sys.stderr.write('  median domain size:    %~.0f\n'.replace('~', max_digit) % median)
        sys.stderr.write('bool variables:          %~d\n'.replace('~', max_digit) % len(self.bool_variables))
        sys.stderr.write('inf domains (y/n):       %~s\n'.replace('~', max_digit) % ('y' if self.inf_dom else 'n'))

        constr_len = sorted(self.stats['constr_len'])
        constr_median = constr_len[len(constr_len) / 2]
        sys.stderr.write('int constraints:         %~d\n'.replace('~', max_digit) % len(self.constraint_matrix))
        sys.stderr.write(
            '  avg len:               %~.2f\n'.replace('~', max_digit) % (sum(constr_len) / float(len(
                self.constraint_matrix))))
        sys.stderr.write('  max len:               %~d\n'.replace('~', max_digit) % constr_len[-1])
        sys.stderr.write('  median len:            %~d\n'.replace('~', max_digit) % constr_median)

        sys.stderr.write('clauses:                 %~d\n'.replace('~', max_digit) % len(self.clauses))
        sys.stderr.write('bool to int:             %~d\n'.replace('~', max_digit) % len(self.bool_to_int))
        sys.stderr.write('opt vector:              %~d\n'.replace('~', max_digit) % len(self.opt_vector))

    def avg_domain_len(self):
        _sum = sorted([dom.len() for v, dom in self.variables.items()])
        median = _sum[len(_sum) / 2]
        return float(sum(_sum)) / float(len(self.variables)), median

    def write_output(self, output):
        if self.instance_name == '':
            sys.stderr.write('an instance name must be given before writing\n')
            sys.exit(1)

        if output == '-':
            output = sys.stdout
        elif os.path.isdir(output):
            output = output + '/' + self.instance_name
        else:
            sys.stderr.write('Error: output isn\'t writeable\n')
            sys.exit(1)

        if self.instance_name == '':
            output += str(datetime.now()).replace(' ', '_').replace(':', '.')

        # only minimization is supported
        opt_vector = self.opt_vector if self.opt_strategy == "minimize" else [(var, -w) for var, w in self.opt_vector]

        self.writer.write(output, self.variables, self.bool_variables, opt_vector, self.constraint_matrix, self.clauses,
                          self.bool_to_int)

    def new_int_variable(self, domain, internal=False):
        if not isinstance(domain, Domain):
            raise TypeError("domain is not of type Domain")

        var = ('x' if not internal else 's') + str(len(self.variables) + 1)
        self.variables[var] = domain

        ILPParser.max_num_digests = max(1, int(ceil(log10(len(self.variables)))))

        return var

    def new_bool_variable(self, internal=False):
        var = ('b' if not internal else '_b') + str(len(self.bool_variables))
        self.bool_variables.add(var)

        # ILPParser.max_num_digests = max(1, int(ceil(log10(len(self.variables)))))

        return var

    def add_to_opt_vector(self, var, weight=1):
        if var in self.variables:
            self.opt_vector.append((var, weight))
        else:
            raise Exception(var + " isn't a known variable")

    def set_opt_strategy(self, strategy):
        if strategy.lower() in ILPParser.opt_strategies:
            self.opt_strategy = strategy.lower()
        else:
            raise Exception("unknown optimization strategy")

    def _constraint_split_le(self, terms, b, reified=None):
        dom = self.variables[terms[0][0]]
        dom = dom.copy(multiplier=terms[0][1])
        s = self.new_int_variable(dom, internal=True)
        self.add_ge_constraint([terms[0], (s, -1)], 0, split=False)

        for t in terms[1:]:
            var, w = t
            dom_n = self.variables[var].copy(multiplier=w)
            dom_n = ILPParser.merge_dom(dom_n, dom)
            sn = self.new_int_variable(dom_n, internal=True)
            self.add_ge_constraint([t, (s, 1), (sn, -1)], 0, split=False)
            s = sn
            dom = dom_n

        self.add_ge_constraint([(s, 1)], b, split=False, reified_var=reified)

    def _constraint_split_eq(self, terms, b, reified=None):
        if len(terms) > 3:
            dom1 = ILPParser.term_domain(self.variables[terms[-2][0]], terms[-2][1])
            dom2 = ILPParser.term_domain(self.variables[terms[-1][0]], terms[-1][1])
            new_dom = ILPParser.merge_dom(dom1, dom2)
            s = self.new_int_variable(new_dom, internal=True)
            self.add_eq_constraint(terms[-2:] + [(s, -1)], 0)
            self._constraint_split_eq(terms[:-2] + [(s, 1)], b, reified=reified)
        else:
            self.add_ge_constraint(terms, b, reified_var=reified)

    def add_ge_constraint(self, terms, b, reified_var=None, split=True):
        self._check_variables(terms)

        if len(terms) > 3 and split and "split" in self.options and self.options["split"] == 1:
            self._constraint_split_eq(terms, b, reified=reified_var)
        elif len(terms) > 3 and split and "split" in self.options and self.options["split"] == 2:
            self._constraint_split_le(terms, b, reified=reified_var)
        else:
            if 'stats' in self.options and self.options['stats']:
                self.stats['constr_len'].append(len(terms))
            self.constraint_matrix.append((terms, b, reified_var))

    def add_le_constraint(self, vars_with_weights, b, reified_var=None):
        return self.add_ge_constraint(ILPParser.inverse_terms(vars_with_weights), -b, reified_var=reified_var)

    def add_gt_constraint(self, vars_with_weights, b, reified_var=None):
        return self.add_ge_constraint(vars_with_weights, b + 1, reified_var=reified_var)

    def add_lt_constraint(self, vars_with_weights, b, reified_var=None):
        return self.add_ge_constraint(ILPParser.inverse_terms(vars_with_weights), -b + 1, reified_var=reified_var)

    def add_eq_constraint(self, vars_with_weights, b, reified_var=None):
        self.add_ge_constraint(vars_with_weights, b, reified_var=reified_var)
        self.add_le_constraint(vars_with_weights, b, reified_var=reified_var)

        return len(self.constraint_matrix) - 1

    def add_ne_constraint(self, terms, b):
        inverse_terms = ILPParser.inverse_terms(terms)
        r = self.new_bool_variable(internal=True)

        self.add_ge_constraint(terms, b + 1, reified_var=(r, True))
        self.add_ge_constraint(inverse_terms, 1 - b, reified_var=(r, False))

        return len(self.constraint_matrix) - 1

    def add_alldiff_constraint(self, *variables):
        if len(variables) < 2:
            raise Exception('alldifferent expects at least two variables')

        index = 1
        for var1 in variables:
            for var2 in variables[index:]:
                r_var = self.new_bool_variable(internal=True)
                self.add_ge_constraint([(var1, 1), (var2, -1)], 1, reified_var=(r_var, True))
                self.add_ge_constraint([(var1, -1), (var2, 1)], 1, reified_var=(r_var, False))
            index += 1

        return len(self.constraint_matrix) - 1

    def add_clause(self, *literals):
        for lit in literals:
            if lit.replace("-", "") not in self.bool_variables:
                raise Exception(lit + " isn't a known boolean variable")

        self.clauses.append(literals)

    def add_bool2int(self, b_var, i_var):
        if b_var not in self.bool_variables and b_var != '0':
            sys.stderr.write("Error: Unknown boolean variable %s\n" % b_var)
            sys.exit(1)
        if i_var not in self.variables:
            sys.stderr.write("Error: Unknown integer variable %s\n" % i_var)
            sys.exit(1)

        self.bool_to_int.append((b_var, i_var))

    def set_instance_name(self, name):
        self.instance_name = name

    def set_inf_bounds(self):
        """ mark the instance of having infinite upper bounds """
        self.inf_dom = True

    def has_inf_bounds(self):
        return self.inf_dom

    def reset(self):
        self.inf_dom = False

        self.opt_vector = []
        self.opt_strategy = 'minimize'
        self.constraint_matrix = []
        self.variables = {}

        self.instance_name = ''

    def _check_variables(self, vars_with_weights):
        for v, w in vars_with_weights:
            if v not in self.variables:
                raise Exception(str(v) + " isn't a known variable")
            elif not isinstance(w, (int, long)):
                raise Exception("weight for %s must be an integer" % v)

    @staticmethod
    def cmp_vars(var):
        if len(var) == 1:
            return str(var)
        return ('%%.%dd' % ILPParser.max_num_digests) % int(var[1:])

    @staticmethod
    def inverse_terms(terms):
        return [(var, -w) for var, w in terms]

    @staticmethod
    def merge_dom(dom1, dom2):
        domains = [dom1, dom2]
        domain_classes = {dom1.__class__, dom2.__class__}
        open_bounds = dom1.has_open_bound() or dom2.has_open_bound()

        if not open_bounds and dom1.len() * dom2.len() <= 10000 and domain_classes != {ContiguousDomain}:
            # closed and enumerable domains are merged by computing all combinations
            dom = sorted(ILPParser._recursive_dom_merge(domains))
            if abs(dom[-1] - dom[0]) == len(dom) - 1:
                # detect and prefer a contiguous domain
                return ContiguousDomain(dom[0], dom[-1])
            else:
                return DomainByEnum(dom)
        else:
            lb = sum([d.lb() for d in domains])
            ub = sum([d.ub() for d in domains])
            return ContiguousDomain(lb, ub)

    @staticmethod
    def _recursive_dom_merge(domains, index=0):
        if len(domains) - 1 == index:
            return domains[index].get_values()
        else:
            values = set()
            for v in ILPParser._recursive_dom_merge(domains, index + 1):
                for d in domains[index].get_values():
                    values.add(d + v)

            return values

    @staticmethod
    def term_domain(domain, w):
        if isinstance(domain, DomainByEnum):
            return DomainByEnum(domain.get_values(), multiplier=w)
        elif isinstance(domain, DomainByMonotonicFunction):
            return DomainByMonotonicFunction(domain.lb(), domain.ub(), domain.fn, multiplier=w)
        elif isinstance(domain, ContiguousDomain):
            return ContiguousDomain(domain.lb(), domain.ub(), multiplier=w)
        else:
            raise TypeError("Domain class not supported")
