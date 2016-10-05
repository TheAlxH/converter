import gzip
import re
import sys

from InputReader import InputReader
from ..domains.continuous.continuous_domain import ContinuousDomain


class PisingerReader(InputReader):
    strategy = 'maximize'

    def __init__(self, **options):
        super(PisingerReader, self).__init__(**options)

        self.var_table = {}
        self.offset = 0
        self.EOF = False

    def parse(self, input_file, offset=0):
        is_gzip = (input_file[-2:] == 'gz') if type(input_file) == str else False

        if input_file != sys.stdin and not is_gzip:
            input_file = open(input_file, "r")
        elif type(input_file) == str:
            input_file = gzip.open(input_file, "r")

        instance = self.parse_one_instance(input_file, offset=offset)

        if not instance:
            return None

        weights, profits, capacity, instance_name = instance
        self.define_variables(profits)
        self.get_constraints(weights, capacity)
        self.get_optimization_vector(profits)
        self.get_optimization_strategy()
        self.parser.set_instance_name(instance_name)

        if input_file != sys.stdin:
            input_file.close()

        return True

    def get_constraints(self, weights, capacity):
        weighted_variables = []

        for i in range(0, len(weights)):
            weighted_variables.append((self.var_table[i], weights[i]))

        self.parser.add_le_constraint(weighted_variables, capacity)

    def get_optimization_strategy(self):
        self.parser.set_opt_strategy(PisingerReader.strategy)

    def get_optimization_vector(self, profits):
        for i in range(0, len(profits)):
            self.parser.add_to_opt_vector(self.var_table[i], profits[i])

    def define_variables(self, internal_representation):
        for var in range(0, len(internal_representation)):
            self.var_table[var] = self.parser.new_int_variable(ContinuousDomain(0, 1))

    def parse_one_instance(self, f, offset=0):
        weights = []
        profits = []
        capacity = None
        instance_name = None

        f.seek(offset)

        for line in iter(f.readline, b''):
            if len(line) < 2:
                continue
            elif line[0] == '-':
                self.offset = f.tell()
                return weights, profits, capacity, instance_name
            elif instance_name is None:
                instance_name = line[0:-1]
            elif line[0].isdigit():
                parts = re.split(',', line)
                weights.append(int(parts[2]))
                profits.append(int(parts[1]))
            elif line[0] == 'c':
                capacity = int(line[1:])

        self.offset = f.tell()
        self.EOF = True

        return None
