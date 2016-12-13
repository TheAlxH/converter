import gzip
import os.path
import os
import re
import sys
import subprocess
import tempfile

from InputReader import InputReader
from ..domains.contiguous.contiguous_domain import ContiguousDomain

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


class FZNReader(InputReader):
    def __init__(self, **options):
        super(FZNReader, self).__init__(**options)
        self.var_table = {}

    def parse(self, input_file, **kwargs):
        if type(input_file) == str and input_file[-2:] == 'gz':
            sys.stderr.write('WARNING: gzip files not supported by FZN reader\n')

        if input_file == sys.stdin:
            tmp = tempfile.NamedTemporaryFile('w', delete=False)
            name = tmp.name
            file_name = input_file.name

            for l in iter(sys.stdin.readline, ''):
                tmp.write(l)

            tmp.close()
        else:
            name = input_file
            file_name = input_file

        fzn_path = os.path.split(__file__)[0] + '/../../gecode/fz'

        if not os.path.isfile(fzn_path):
            sys.stderr.write('ERROR: ./gecode/fz not found. Build first...\n')
            sys.exit(1)

        sub = subprocess.Popen([fzn_path, name], stdout=subprocess.PIPE, universal_newlines=True)

        self.converter.set_instance_name(os.path.basename(os.path.splitext(file_name)[0]))
        self.parse_instance(sub.stdout)

        if input_file == sys.stdin:
            os.remove(name)

        if sub.wait() != 0:
            sys.stderr.write('ERROR: fzn parsing aborted\n')
            sys.exit(sub.returncode)

        return True

    def parse_instance(self, f):
        for line in iter(f.readline, b''):
            self.parse_line(line.rstrip())

        return None

    def parse_line(self, line):
        split = line.find(' ')
        token = line[:split]
        split += 1

        if token == '[INT]':
            self.parse_variable(line[split:])
        elif token == '[BOOL]':
            self.parse_variable(line[split:], is_bool=True)
        elif token == '[CONSTRAINT]':
            self.parse_constraint(line[split:])
        elif token == '[ALLDIFFERENT]':
            self.parse_alldiff(line[split:])
        elif token == '[REIFIED]':
            self.parse_reified(line[split:])
        elif token == '[OPTIMIZATION]':
            self.parse_optimization(line[split:])
        elif token == '[DISJUNCTION]':
            self.parse_disjunction(line[split:])
        elif token == '[BOOL2INT]':
            self.parse_bool2int(line[split:])

    def parse_variable(self, line, is_bool=False):
        if is_bool:
            var = line.strip()
            self.var_table[var] = self.converter.new_bool_variable()
        else:
            var = line.split()[0].strip()
            interval = re_int_interval.search(line)
            if interval is not None:
                lb = int(interval.groups()[0])
                ub = int(interval.groups()[1])
                var_id = self.converter.new_int_variable(ContiguousDomain(lb, ub))
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

        fn = getattr(self.converter, rel_map[rel])
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
        self.converter.set_opt_strategy(strategy)
        self.converter.add_to_opt_vector(self.var_table[var])

    def parse_alldiff(self, line):
        variables = line.strip().split()
        self.converter.add_alldiff_constraint(*[self.var_table[v] for v in variables])

    def parse_disjunction(self, line):
        literals = set(line.strip().split())
        if '1' in literals:
            return
        if '0' in literals:
            literals.remove('0')
        self.converter.add_clause(*[self._get_bool_var(lit) for lit in literals])

    def parse_bool2int(self, line):
        b, i = line.strip().split()
        if b != '1' and b != '0':
            b = self.var_table[b]

        self.converter.add_bool2int(b, self.var_table[i])

    def _get_bool_var(self, b):
        if b[0] == '-':
            return '-' + self.var_table[b[1:]]
        else:
            return self.var_table[b]
