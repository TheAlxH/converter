from continuous_domain_iterator import ContinuousDomainIterator
from continuous_domain import ContinuousDomain
from ..inf_len_exception import InfLenException
from ..inf_bound_exception import InfBoundException
import math


class SemiContinuousDomain(ContinuousDomain):
    def __init__(self, lb, ub, multiplier=1):
        super(SemiContinuousDomain, self).__init__(lb, ub, multiplier)
        self._lb = lb
        self._ub = ub
        self.inf_bound = self._lb == SemiContinuousDomain.INF_N or self._ub == SemiContinuousDomain.INF_P

    def copy(self, multiplier=1):
        return SemiContinuousDomain(self._lb, self._ub, multiplier=multiplier)

    def lb(self):
        lb = super(SemiContinuousDomain, self).lb()
        return 0 if lb > 0 else lb

    def ub(self):
        ub = super(SemiContinuousDomain, self).ub()
        return 0 if ub < 0 else ub

    def len(self):
        return super(SemiContinuousDomain, self).len() + int(self._lb > 0 or self._ub < 0)

    def __iter__(self):
        if self._lb == ContinuousDomain.INF_N and self._ub == ContinuousDomain.INF_P:
            return ContinuousDomainIterator(self, self.multiplier)
        else:
            return self._value_generator()

    def _iter_values(self):
        if self.multiplier > 0:
            return xrange(self._lb, self._ub + 1, self.multiplier)
        else:
            return xrange(-1 * self._ub, -1 * self._lb + 1, abs(self.multiplier))

    def _value_generator(self):
        if not self.inf_bound:
            if self._lb > 0:
                yield 0
            for v in self._iter_values():
                yield v
            if self._ub < 0:
                yield 0

    def __len__(self):
        if self.inf_bound:
            raise InfLenException
        return self.len()

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.start < 0 or item.stop < 0:
                raise IndexError('reverse traversal is not supported')
            elif item.start >= item.stop or item.start >= self.len():
                return []

            if self._lb > 0:
                _item = slice(max(0, item.start - 1), max(0, item.stop - 1), 1)
                spr = super(SemiContinuousDomain, self).__getitem__(_item)
                return ([0] + spr) if item.start == 0 else spr
            elif self._ub < 0:
                l = self.len()
                stop = min(item.stop, l - 1)
                if not self.inf_bound:
                    return range(self._lb + item.start, self._lb + stop) + ([0] if item.stop >= l else [])
                else:
                    _item = slice(max(0, item.start - 1), max(0, item.stop - 1), 1)
                    spr = super(SemiContinuousDomain, self).__getitem__(_item)
                    if len(spr) < stop - item.start:
                        return spr + [0]
                    else:
                        return spr

            else:
                return super(SemiContinuousDomain, self).__getitem__(item)
        else:
            if self._lb > 0:
                v = 0 if item == 0 else super(SemiContinuousDomain, self).__getitem__(item - 1)
                if v > self._ub:
                    raise IndexError
                else:
                    return v
            elif self._ub < 0 and not self.inf_bound:
                return 0 if item == self.len() - 1 else super(SemiContinuousDomain, self).__getitem__(item)
            elif self._ub < 0:
                return 0 if item == 0 else super(SemiContinuousDomain, self).__getitem__(item - 1)
            else:
                return super(SemiContinuousDomain, self).__getitem__(item)

    def get_values_asc(self):
        if self.has_open_bound():
            raise InfBoundException
        else:
            if self._lb > 0:
                yield 0

            for v in super(SemiContinuousDomain, self).get_values_asc():
                yield v

            if self._ub < 0:
                yield 0

    def dump_values(self):
        values = super(SemiContinuousDomain, self).dump_values()
        if self._lb > 0:
            return [0] + values
        elif self._ub < 0:
            return values + [0]
        else:
            return values

    @staticmethod
    def _fn(i):
        return (i + 1) / 2 * (1 if i & 1 == 0 else -1)

    def export_self(self):
        return self.__class__.__name__, [self._lb, self._ub, self.multiplier]

    @staticmethod
    def import_self(lb, ub, multiplier):
        return SemiContinuousDomain(lb, ub, multiplier=multiplier)

    def __str__(self):
        if not self.inf_bound:
            return str([i for i in self])
        else:
            return str("[...]")
