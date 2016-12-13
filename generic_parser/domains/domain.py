from abc import ABCMeta, abstractmethod


class Domain:
    __metaclass__ = ABCMeta

    def __init__(self, multiplier):
        self.inf_bound = False
        self.multiplier = multiplier

    @abstractmethod
    def lb(self):
        pass

    @abstractmethod
    def ub(self):
        pass

    def has_open_bound(self):
        return self.inf_bound

    @abstractmethod
    def len(self):
        pass

    @abstractmethod
    def copy(self, multiplier=1):
        pass

    @abstractmethod
    def get_values(self):
        pass

    @abstractmethod
    def get_values_asc(self):
        pass

    @abstractmethod
    def export_self(self):
        pass

    @staticmethod
    def import_self(*args):
        pass

    def __le__(self, dom2):
        if dom2.inf_bound:
            return True
        elif self.inf_bound:
            return False
        else:
            return len(self) <= len(dom2)

    def __ge__(self, dom2):
        return dom2 <= self

    def __eq__(self, dom2):
        if self.inf_bound and dom2.inf_bound:
            return True
        elif self.inf_bound or dom2.inf_bound:
            return False
        else:
            return len(self) == len(dom2)

    def __ne__(self, dom2):
        return not self.__eq__(dom2)

    def __lt__(self, dom2):
        if self.inf_bound:
            return False
        elif dom2.inf_bound:
            return True
        else:
            return len(self) < len(dom2)

    def __gt__(self, dom2):
        return dom2.__lt__(self)
