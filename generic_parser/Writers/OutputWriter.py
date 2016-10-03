from abc import ABCMeta, abstractmethod


class OutputWriter:
    """
    :type parser: ILPParser
    :type output_file: file
    """
    __metaclass__ = ABCMeta

    def __init__(self, **options):
        self.parser = None
        self.output_file = None

    def set_parser(self, parser):
        self.parser = parser

    @abstractmethod
    def write(self, output, int_vars_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        pass
