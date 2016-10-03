import collections
import re
import sys

from InputReader import InputReader
from ..domains.continuous.continuous_domain import ContinuousDomain

keywords_max = ['MAXIMIZE', 'MAXIMUM', 'MAX']
keywords_min = ['MINIMIZE', 'MINIMUM', 'MIN']
keywords_obj = keywords_max + keywords_min
keywords_con = ['SUBJECT TO', 'SUCH THAT', 'ST', 'S.T.']
keywords_bnd = ['BOUNDS']
keywords_bin = ['BINARY', 'BINARIES', 'BIN']
keywords_gen = ['GENERALS', 'GENERAL', 'GEN']
keywords_var = ['SEMIS', 'SEMI-CONTINUOUS', 'SEMI'] + keywords_bnd + keywords_bin + keywords_gen
keywords = ['END'] + keywords_obj + keywords_con + keywords_var


def tokenize(s):
    Token = collections.namedtuple('Token', ['typ', 'value', 'line', 'column'])

    token_specification = [
        ('KEYWORD', '|'.join('(^%s)' % kw for kw in keywords)),
        ('CONST', '(-?(infinity|inf))|free'),
        ('LABEL', r'\w+:'),
        ('NUMBER', r'\d+(\.\d*)?'),
        ('ARITHMETIC', r'[*+-]'),
        ('OPERATOR', r'(?:<=)|(=<)|<|(>=)|(=>)|>|=|\[|\]'),
        ('ID', r'\w+'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]'),
        ('COMMENT', r'\\[^\n]*'),
    ]
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    get_token = re.compile(tok_regex, flags=re.I | re.M).match
    line = 1
    pos = line_start = 0

    mo = get_token(s)
    while mo is not None:
        typ = mo.lastgroup
        if typ == 'NEWLINE':
            line_start = pos
            line += 1
        elif typ != 'SKIP' and typ != 'COMMENT':
            val = mo.group(typ)
            # if typ == 'ID' and val.upper() in keywords:
            #     typ = 'KEYWORD'
            yield Token(typ, val, line, mo.start() - line_start)
        pos = mo.end()
        mo = get_token(s, pos)
    if pos != len(s):
        raise RuntimeError('Unexpected character %r on line %d' % (s[pos], line))


# default domain
default_dom = ContinuousDomain(0, float('inf'))
free_dom = ContinuousDomain(-float('inf'), float('inf'))


class LPReader(InputReader):
    def __init__(self, **options):
        super(LPReader, self).__init__(**options)
        self.tokens = None
        self.var_table = {}
        self.op_map = None
        self.constraints = {}

    def set_parser(self, parser):
        super(LPReader, self).set_parser(parser)
        self.op_map = {
            '=': self.parser.add_eq_constraint,
            '!=': self.parser.add_ne_constraint,
            '<': self.parser.add_le_constraint,
            '>': self.parser.add_ge_constraint,
            '<=': self.parser.add_le_constraint,
            '>=': self.parser.add_ge_constraint,
            '=<': self.parser.add_le_constraint,
            '=>': self.parser.add_ge_constraint
        }

    def parse(self, input_file, **kwargs):
        self.parser.set_instance_name(input_file)

        # TODO gzip
        if type(input_file) == str:
            with open(input_file) as inst:
                s = inst.read()
        elif type(input_file) == file:
            s = input_file.read()
        else:
            sys.stderr.write("Error: input no readable\n")
            sys.exit(1)

        self.tokens = tokenize(s)

        section = self.tokens.next().value
        self.dispatch_section(section)

        for op, constraints in self.constraints.items():
            for c in constraints:
                op(*c)

    def parse_obj_section(self, kw):
        n = None
        minus = False

        if kw.upper()[0:3] == 'MAX':
            self.parser.set_opt_strategy('maximize')

        for token in self.tokens:
            if token.typ == 'KEYWORD':
                self.dispatch_section(token.value)
                return

            if token.typ == 'NUMBER':
                n = int(token.value)
            elif token.typ == 'ARITHMETIC':
                minus = token.value == '-'
            elif token.typ == 'ID':
                if n is None:
                    n = 1
                var = self.get_var(token.value)
                self.parser.add_to_opt_vector(var, n * (-1 if minus else 1))
                n = None
                minus = False

    def parse_constraints_section(self):
        terms = []
        n = op = None
        minus = False

        for token in self.tokens:
            if token.typ == 'KEYWORD':
                self.dispatch_section(token.value)
                return

            if token.typ == 'ID':
                var = self.get_var(token.value)
                if n is None:
                    n = 1
                terms.append((var, n * (-1 if minus else 1)))
                n, minus = None, False
            elif token.typ == 'ARITHMETIC':
                minus = token.value == '-'
            elif token.typ == 'NUMBER':
                if op is None:
                    n = int(token.value)
                else:
                    # delay constraints registration for more domain knowledge
                    if op in self.constraints:
                        self.constraints[op].append((terms, int(token.value)))
                    else:
                        self.constraints[op] = [(terms, int(token.value))]
                    n = op = None
                    terms = []
            elif token.typ == 'OPERATOR':
                if token.value == '[' or token.value == ']':
                    raise Exception("quadratic expressions not supported")
                op = self.op_map[token.value]

    def parse_bounds_section(self):
        lb = ub = var = op = None
        line = -1

        for token in self.tokens:
            if token.typ == 'KEYWORD':
                var = self.var_table[var]
                self.parser.variables[var] = ContinuousDomain(lb if lb is not None else 0,
                                                              ub if ub is not None else float('inf'))
                self.dispatch_section(token.value)
                return

            if token.line > line and var is not None:
                var = self.var_table[var]
                dom = ContinuousDomain(lb if lb is not None else 0, ub if ub is not None else float('inf'))
                self.parser.variables[var] = dom
                lb = ub = var = None

            line = token.line

            if token.typ == 'ID':
                var = token.value
            elif token.typ == 'NUMBER':
                if var is None:
                    lb = int(token.value)
                elif op == '<=':
                    ub = int(token.value)
                elif op == '>=':
                    lb = int(token.value)
            elif token.typ == 'CONST':
                if token.value == 'free':
                    lb, ub = -float('inf'), float('inf')
                elif token.value.upper()[0:3] == 'INF':
                    if op == '<=' and token.value[0] != '-':
                        ub = float('inf')
                    elif op == '>=' and token.value[0] == '-':
                        lb = -float('inf')
                    else:
                        raise Exception('corrupt bounds in line %d' % token.line)
            elif token.typ == 'OPERATOR':
                op = token.value

    def parse_binaries_section(self, kw):
        if kw.upper()[0:3] == 'BIN':
            dom = ContinuousDomain(0, 1)
        elif kw.upper()[0:3] == 'GEN':
            dom = free_dom
        else:
            raise Exception('section not supported: %s' % kw)

        for token in self.tokens:
            if token.typ == 'KEYWORD':
                self.dispatch_section(token.value)
                return

            if token.typ == 'ID':
                var = self.get_var(token.value)
                self.parser.variables[var] = dom

    def get_var(self, id):
        if id in self.var_table:
            return self.var_table[id]
        else:
            self.var_table[id] = self.parser.new_int_variable(default_dom)
            return self.var_table[id]

    def dispatch_section(self, section):
        if section.upper() in keywords_obj:
            self.parse_obj_section(section)
        elif section.upper() in keywords_con:
            self.parse_constraints_section()
        elif section.upper() in keywords_bnd:
            self.parse_bounds_section()
        elif section.upper() in keywords_bin or section.upper() in keywords_gen:
            self.parse_binaries_section(section)
