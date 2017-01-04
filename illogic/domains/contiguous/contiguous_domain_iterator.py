class ContiguousDomainIterator:
    """
    :type dom: ContiguousDomain
    """
    def __init__(self, dom, multiplier):
        self.dom = dom
        self.inner_state = True
        self.expand = None
        self.multiplier = multiplier

        if dom.lb() == dom.INF_N and dom.ub() == dom.INF_P:
            self.i = 0
            self.expand = self.zigzag
        elif dom.lb() == dom.INF_N:
            self.i = dom.ub() + 1
            self.expand = self.desc
        else:
            self.i = dom.lb() - 1
            self.expand = self.inc

    def next(self):
        return self.expand()

    def inc(self):
        if self.i >= self.dom.ub():
            raise StopIteration

        self.i += 1
        return self.i * self.multiplier

    def desc(self):
        self.i -= 1
        return self.i * self.multiplier

    def zigzag(self):
        if self.inner_state:
            self.inner_state = not self.inner_state
            return -1 * self.i * self.multiplier
        else:
            self.inner_state = not self.inner_state
            self.i += 1
            return self.i * self.multiplier
