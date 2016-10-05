from .. import json_reader
import sys

from InputReader import InputReader
from ..domains.continuous.continuous_domain import ContinuousDomain
from ..domains.domain_by_enum import DomainByEnum
from ..domains.domain_by_monotonic_function import DomainByMonotonicFunction


class IncReader(InputReader):
    def __init__(self, **options):
        super(IncReader, self).__init__(**options)
        self.options = options
        if 'lb' in options or 'ub' in options:
            sys.stderr.write('WARNING: overriding bounds is not supported in INC-reader\n')

    def set_parser(self, parser):
        super(IncReader, self).set_parser(parser)

    def parse(self, input_file, **kwargs):
        self.parser.set_instance_name(input_file)

        def dummy_logger(*args, **kwargs):
            pass

        booleans, clauses, bool2int, domains, constraints, opt = json_reader.read(input_file, dummy_logger)

        bounds_override = 'lb' in self.options or 'ub' in self.options
        if bounds_override:
            for var, dom in domains.items():
                if dom.has_open_bound():
                    sys.stderr.write('ERROR: overriding bounds is not supported in INC-reader\n')
                    sys.exit(1)
                else:
                    self.parser.variables[var] = dom
        else:
            self.parser.variables = domains

        self.parser.bool_variables = booleans
        self.parser.clauses = clauses
        self.parser.bool_to_int = bool2int
        self.parser.opt = opt

        for c in constraints:
            self.parser.add_ge_constraint(c.terms, c.b, c.reified)
