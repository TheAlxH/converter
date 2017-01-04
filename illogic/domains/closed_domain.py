from abc import ABCMeta
from domain import Domain


class ClosedDomain(Domain):
    __metaclass__ = ABCMeta

    def __init__(self, values, multiplier=1):
        super(ClosedDomain, self).__init__(multiplier)
        self.values = values

    def copy(self, multiplier=1):
        return ClosedDomain(self.values, multiplier=multiplier)

    def lb(self):
        return self.values[0]

    def ub(self):
        return self.values[-1]

    def get_values(self):
        return self.values

    def get_values_asc(self, multiplier=1, start=0):
        if multiplier > 0:
            for i in self.values[start:]:
                yield i * multiplier
        else:
            for i in reversed(self.values[:len(self.values) - start]):
                yield i * multiplier

    def get_values_desc(self, multiplier=1, start=0):
        if multiplier > 0:
            for i in reversed(self.values[:len(self.values) - start]):
                yield i * multiplier
        else:
            for i in self.values[start:]:
                yield i * multiplier

    def search(self, v):
        """
        Searches and returns the minimal value v' that is greater equal to v.
        -1 is returned else.
        """
        if v < self.values[0] or v > self.values[-1]:
            raise IndexError('element not found')

        return self.values[self._bin_search_recursive(v, 0, len(self.values) - 1)]

    def _bin_search_recursive(self, v, start, end):
        """
        Recursive helper function for DomainHistory.bin_search.
        """
        if end < start:
            return start

        mid = (start + end) / 2
        if self.values[mid] == v:
            return mid
        elif self.values[mid] < v:
            return self._bin_search_recursive(v, mid + 1, end)
        else:
            return self._bin_search_recursive(v, start, mid - 1)

    def find_next(self, v):
        """
        Finds the successor of an element, if available.
        """
        if v + 1 < self.values[0] or v + 1 > self.values[-1]:
            raise IndexError('element not found')

        index = self._bin_search_recursive(v, 0, len(self.values) - 1)

        if index < len(self.values) - 1:
            return self.values[index + 1]
        else:
            raise IndexError('element not found')

    def find_prev(self, v):
        """
        Finds the predecessor of an element, if available.
        """
        if v - 1 < self.values[0] or v - 1 > self.values[-1]:
            raise IndexError('element not found')

        index = self._bin_search_recursive(v, 0, len(self.values) - 1)

        if index > 0:
            return self.values[index - 1]
        else:
            raise IndexError('element not found')

    def has(self, v):
        """
        Checks if the element v is in the value list
        """
        return v in self.values

    def index(self, v):
        """
        Searches the index in the value list where a new value would be inserted.
        """
        return self._bin_search_recursive(v, 0, self.__len__() - 1)

    def __len__(self):
        return len(self.values)

    def len(self):
        return self.__len__()

    def __str__(self):
        if len(self.values) > 20:
            return str(self.values[0:5]) + " ... " + str(self.values[-5:]) + " # " + str(len(self.values))
        return str([i for i in self.values])

    def __repr__(self):
        return self.__str__()

    def export_self(self):
        return self.__class__.__name__, [self.values]

    @staticmethod
    def import_self(*args):
        return args[0](*args[1:])
