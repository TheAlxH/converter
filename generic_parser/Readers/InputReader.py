from abc import ABCMeta, abstractmethod


class InputReader:
    __metaclass__ = ABCMeta

    def __init__(self, **options):
        self.parser = None

    def set_parser(self, parser):
        self.parser = parser

    @abstractmethod
    def parse(self, input_file, **kwargs):
        pass
