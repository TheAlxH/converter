from abc import ABCMeta, abstractmethod


class InputReader:
    __metaclass__ = ABCMeta

    def __init__(self, **options):
        self.converter = None

    def set_converter(self, converter):
        self.converter = converter

    @abstractmethod
    def parse(self, input_file, **kwargs):
        pass
