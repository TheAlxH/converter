from abc import ABCMeta, abstractmethod


class OutputWriter:
    """
    :type converter: ILPParser
    :type output_file: file
    """
    __metaclass__ = ABCMeta

    def __init__(self, **options):
        self.converter = None
        self.output_file = None
        self.options = options

    def set_converter(self, converter):
        self.converter = converter

    @abstractmethod
    def write(self, output, int_vars_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        pass
