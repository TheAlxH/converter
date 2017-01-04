from functools import partial


class Constraint:
    def __init__(self, terms, b, reified=None):
        self.terms = terms
        self.b = b
        self.touched = False
        self.is_reified_copy = False
        self.vars = {t[0] for t in self.terms}
        if type(reified) == str:
            self.reified = (reified, True)
        else:
            self.reified = reified

    def reorder(self, variables):
        fn = partial(Constraint._sort, variables)
        terms = sorted(self.terms, key=fn)
        return Constraint(terms, self.b, reified=self.reified)

    def get_terms(self):
        return {var: weight for var, weight in self.terms}

    def has_var(self, var):
        return var in self.vars

    def __str__(self):
        return ('%s >= %d' % (str(self.terms), self.b)) \
               + ((" <-> %s" % self.reified[0]) if self.reified is not None else "")

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def _sort(variables, term):
        try:
            return variables.index(term[0])
        except ValueError:
            return -1
