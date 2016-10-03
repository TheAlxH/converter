from ..domain import Domain
from ..inf_len_exception import InfLenException
from ..inf_bound_exception import InfBoundException
import math


class ContinuousDomain(Domain):
    INF_P = float('inf')
    INF_N = -float('inf')

    def __init__(self, lb, ub, multiplier=1):
        super(ContinuousDomain, self).__init__(multiplier)
        self._lb = lb
        self._ub = ub
        self.inf_bound = self._lb == ContinuousDomain.INF_N or self._ub == ContinuousDomain.INF_P

    def copy(self, multiplier=1):
        return ContinuousDomain(self._lb, self._ub, multiplier=multiplier * self.multiplier)

    def lb(self):
        return self.multiplier * self._lb if self.multiplier > 0 else self.multiplier * self._ub

    def ub(self):
        return self.multiplier * self._lb if self.multiplier < 0 else self.multiplier * self._ub

    def len(self):
        return ContinuousDomain.INF_P if self.inf_bound else self._ub - self._lb + 1

    def __iter__(self):
        lb, ub = self.lb(), self.ub()

        if not self.inf_bound or lb != ContinuousDomain.INF_N:
            # ascending
            t, m = lb, abs(self.multiplier)
            while t <= ub:
                yield t
                t += m
        elif ub != ContinuousDomain.INF_P:
            # descending
            t, m = ub, -abs(self.multiplier)
            while True:
                yield t
                t += m
        else:
            # zigzag
            i = 0
            while True:
                yield self.multiplier * int(math.ceil(i / 2.0)) * (-1 if i & 1 == 0 else 1)
                i += 1

    def __len__(self):
        if self.inf_bound:
            raise InfLenException
        return self._ub - self._lb + 1

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.start < 0 or item.stop < 0:
                raise IndexError('reverse traversal is not supported')

            if self._lb == ContinuousDomain.INF_N and self._ub == ContinuousDomain.INF_P:
                return sorted([self.multiplier * ContinuousDomain._fn(i) for i in xrange(item.start, item.stop)])
            elif self._lb == ContinuousDomain.INF_N:
                return [self.multiplier * i for i in xrange(self._ub - item.stop + 1, self._ub - item.start + 1)]
            else:
                if not self.inf_bound and item.start > self.__len__() - 1:
                    return []
                else:
                    stop = min(item.stop, self.__len__()) if not self.inf_bound else item.stop
                    return [self.multiplier * i for i in xrange(self._lb + item.start, self._lb + stop)]
        else:
            if item < 0:
                raise IndexError('reverse traversal is not supported')

            if self.inf_bound or item < self.__len__():
                if self._lb == ContinuousDomain.INF_N and self._ub == ContinuousDomain.INF_P:
                    return self.multiplier * int(math.ceil(item / 2.0)) * (-1 if item & 1 == 0 else 1)
                elif self._lb == ContinuousDomain.INF_N:
                    return self.multiplier * (self._ub - item)
                else:
                    return self.multiplier * (self._lb + item)
            else:
                raise IndexError('list index out of range')

    def get_values(self):
        return self

    def get_values_asc(self):
        if self.has_open_bound():
            raise InfBoundException
        else:
            if self.multiplier > 0:
                for i in xrange(self._lb, self._ub + 1):
                    yield self.multiplier * i
            else:
                for i in reversed(xrange(self._lb, self._ub + 1)):
                    yield self.multiplier * i

    def dump_values(self):
        if self.inf_bound:
            raise InfBoundException('values of open domains can\'t be dumped')
        return [i for i in self.get_values_asc()]

    @staticmethod
    def _fn(i):
        return (i + 1) / 2 * (1 if i & 1 == 0 else -1)

    def export_self(self):
        return self.__class__.__name__, [self._lb, self._ub, self.multiplier]

    @staticmethod
    def import_self(lb, ub, multiplier):
        return ContinuousDomain(lb, ub, multiplier=multiplier)

    def __str__(self):
        if not self.inf_bound:
            return str([i for i in self])
        else:
            return str("[...]")

    def __repr__(self):
        return self.__str__()
