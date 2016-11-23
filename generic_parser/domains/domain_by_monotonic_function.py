from domain import Domain
from .inf_len_exception import InfLenException
import base64
import marshal
import types


class DomainByMonotonicFunction(Domain):
    def __init__(self, lb, ub, fn, multiplier=1):
        super(DomainByMonotonicFunction, self).__init__(multiplier)
        self.i = lb - 1
        self._lb = lb
        self._ub = ub
        self.fn = fn
        self.inf_bound = ub == float("inf")
        self.dir = 1 if self._lb < self._ub else -1
        self.multiplier = multiplier

        if type(lb) != int:
            raise TypeError("lb must be of type int")

    def copy(self, multiplier=1):
        if multiplier * self.multiplier < 0:
            lb, ub = self._ub, self._lb
        return DomainByMonotonicFunction(lb, ub, self.fn, multiplier=multiplier)

    def len(self):
        return float("inf") if self.inf_bound else abs(self._ub - self._lb)

    def lb(self):
        return self.fn(self._lb) * self.multiplier

    def ub(self):
        return self.fn(self._ub) * self.multiplier

    def len(self):
        return float('inf') if self.inf_bound else abs(self._ub - self._lb)

    def copy(self, multiplier=1):
        return DomainByMonotonicFunction(self._lb, self._ub, self.fn, multiplier=self.multiplier * multiplier)

    def __iter__(self):
        i = 0
        if self.multiplier > 0:
            while self._lb + i != self._ub + self.dir:
                yield self.multiplier * self.fn(self._lb + i)
                i += self.dir
        else:
            _dir = -self.dir
            while self._lb + _dir != self._ub + i:
                yield self.multiplier * self.fn(self._ub + i)
                i += _dir

    def get_values(self):
        return self

    def get_values_asc(self):
        if self.inf_bound and self.dir < 0:
            raise Exception('values of open domains can\'t be provided in ascending order')
        return self

    def dump_values(self):
        if self.inf_bound:
            raise Exception('values of open domains can\'t be dumped')
        return [i for i in self.get_values_asc()]

    def __len__(self):
        if self.inf_bound:
            raise InfLenException
        return abs(self._ub - self._lb) + 1

    def export_self(self):
        fn = marshal.dumps(self.fn.func_code)
        fn = base64.encodestring(fn)
        return self.__class__.__name__, [self._lb, self._ub, fn, self.multiplier]

    @staticmethod
    def import_self(lb, ub, fn, multiplier):
        fn = base64.decodestring(fn)
        fn = marshal.loads(fn)
        fn = types.FunctionType(fn, {}, 'fn')
        return DomainByMonotonicFunction(lb, ub, fn)

    def __getitem__(self, item):
        if isinstance(item, slice):
            piece = []
            for i in xrange(item.start, item.stop):
                try:
                    index = self._get_index(i)
                except IndexError:
                    break
                piece.append(self.fn(index) * self.multiplier)
            return piece
        else:
            index = self._get_index(item)
            if self.dir < 0:
                return self.fn(index) * self.multiplier
            else:
                return self.fn(index) * self.multiplier

    def _get_index(self, item):
        if not self.inf_bound and item > abs(self._ub - self._lb):
            raise IndexError('list index out of range')
        elif item < 0:
            raise IndexError('negative indexes are not supported')

        if self.dir < 0:
            return self._lb - item
        else:
            return self._lb + item