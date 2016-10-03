import gzip
import os.path
import re
import sys

from InputReader import InputReader
from ..domains.continuous.continuous_domain import ContinuousDomain

re_int_interval = re.compile('\[(-?\d+)\.\.(-?\d+)\]')
re_constraint_split = re.compile('^([^!=<>]+)(!=|=|>=|<=|>|<)(.+)$')
re_constraint = re.compile('(([-+]?\d*)(\w+\d+))')

rel_map = {
    '=': 'add_eq_constraint',
    '!=': 'add_ne_constraint',
    '<': 'add_lt_constraint',
    '>': 'add_gt_constraint',
    '<=': 'add_le_constraint',
    '>=': 'add_ge_constraint'
}


class FZNImfReader(InputReader):
    def __init__(self, convert_float=False):
        super(FZNImfReader, self).__init__()
        self.var_table = {}

    def parse(self, input_file, **kwargs):
        is_gzip = (input_file[-2:] == 'gz') if type(input_file) == str else False

        if input_file != sys.stdin and not is_gzip:
            input_file = open(input_file, "r")
        elif type(input_file) == str:
            input_file = gzip.open(input_file, "r")

        self.parser.set_instance_name(os.path.basename(os.path.splitext(input_file.name)[0]))
        self.parse_instance(input_file)

        input_file.close()
        return True

    def parse_instance(self, f):
        for line in iter(f.readline, b''):
            self.parse_line(line)

        return None

    def parse_line(self, line):
        token = line[:3]

        if token == '[V]':
            self.parse_variable(line[3:-1])
        elif token == '[B]':
            self.parse_variable(line[3:-1], is_bool=True)
        elif token == '[C]':
            self.parse_constraint(line[3:-1])
        elif token == '[A]':
            self.parse_alldiff(line[3:-1])
        elif token == '[R]':
            self.parse_reified(line[3:-1])
        elif token == '[O]':
            self.parse_optimization(line[3:-1])
        elif token == '[D]':
            self.parse_disjunction(line[3:-1])
        elif token == '[2]':
            self.parse_bool2int(line[3:-1])

    def parse_variable(self, line, is_bool=False):
        if is_bool:
            var = line.strip()
            self.var_table[var] = self.parser.new_bool_variable()
        else:
            var = line.split()[0].strip()
            interval = re_int_interval.search(line)
            if interval is not None:
                lb = int(interval.groups()[0])
                ub = int(interval.groups()[1])
                var_id = self.parser.new_int_variable(ContinuousDomain(lb, ub))
            else:
                raise Exception("not implemented yet")  # TODO

            self.var_table[var] = var_id

    def parse_constraint(self, line, translate_only=False):
        line = line.replace(" ", "").replace("+-", "-").replace("--", "+").replace("-+", "-").replace("++", "+")
        terms, rel, c = re_constraint_split.search(line).groups()

        if rel not in rel_map:
            raise Exception(rel + " does not exist in rel map")

        c = int(c)
        new_terms = []
        for _, w, var in re_constraint.findall(terms):
            if w == '-' or w == '+' or w == '':
                w += "1"

            if var not in self.var_table:
                raise Exception(var + " does not exist in var table")

            new_terms.append((self.var_table[var], int(w)))

        fn = getattr(self.parser, rel_map[rel])
        if not translate_only:
            fn(new_terms, c)
        else:
            return new_terms, rel, c, fn

    def parse_reified(self, line):
        line = line.replace(' ', '')
        constraint, reified_var = line.split('<->')
        terms, rel, c, fn = self.parse_constraint(constraint, True)
        fn(terms, c, reified_var=self.var_table[reified_var])

    def parse_optimization(self, line):
        strategy, var = line.strip().split()
        self.parser.set_opt_strategy(strategy)
        self.parser.add_to_opt_vector(self.var_table[var])

    def parse_alldiff(self, line):
        variables = line.strip().split()
        self.parser.add_alldiff_constraint(*[self.var_table[v] for v in variables])

    def parse_disjunction(self, line):
        literals = set(line.strip().split())
        if '1' in literals:
            return
        if '0' in literals:
            literals.remove('0')
        self.parser.add_clause([self.var_table[lit] for lit in literals])

    def parse_bool2int(self, line):
        b, i = line.strip().split()
        if b != '1' and b != '0':
            b = self.var_table[b]

        self.parser.add_bool2int(b, self.var_table[i])
