from domain import Domain


class DomainByEnum(Domain):
    def __init__(self, values, multiplier=1):
        super(DomainByEnum, self).__init__(multiplier)
        if multiplier == 1:
            self.values = list(values)
        elif multiplier > 0:
            self.values = [self.multiplier * v for v in values]
        else:
            self.values = [self.multiplier * v for v in reversed(values)]

    def __len__(self):
        return len(self.values)

    def len(self):
        return self.__len__()

    def copy(self, multiplier=1):
        return DomainByEnum(self.values, multiplier=multiplier)

    def get_values(self):
        return self.values

    def get_values_asc(self):
        return self.values

    def lb(self):
        return self.values[0]

    def ub(self):
        return self.values[-1]

    def export_self(self):
        return self.__class__.__name__, [self.values, self.multiplier]

    @staticmethod
    def import_self(values, multiplier):
        return DomainByEnum(values, multiplier=multiplier)

    def __str__(self):
        if len(self.values) > 20:
            return str(self.values[0:5]) + " ... " + str(self.values[-5:])
        return str([i for i in self.get_values()])

    def __repr__(self):
        return self.__str__()
