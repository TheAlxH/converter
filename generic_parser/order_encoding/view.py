class View:
    def __init__(self, a, x, rel, c, annotation=None):
        """ (ax rel c)# """
        self.a = a
        self.x = x
        self.rel = rel
        self.c = c
        self.annotation = annotation if annotation is not None else ''

    def __str__(self):
        return '(%s%s %s %0.f)%s#' % (str(self.a) if self.a != 1 else '', self.x, self.rel, self.c, self.annotation)

    def __repr__(self):
        return self.__str__()


class SignedView(View):
    def __init__(self, signed, a, x, rel, c, annotation=None):
        View.__init__(self, a, x, rel, c, annotation)
        self.signed = signed

    def __str__(self):
        return '%sp%s' % ('-' if self.signed else '', View.__str__(self)[:-1])
