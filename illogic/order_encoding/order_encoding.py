import math

from ..incremental_grounding.domain_chunk import DomainChunk
from early_exit_exception import EarlyExitException
from view import SignedView
from datetime import datetime

stats = {
    "call": 0,
    "a>0": 0,
    "a<0": 0,
    "for": 0,
    "trans": 0,
    "trans_count": 0
}


class OrderEncoding:
    def __init__(self, dom, lb_g, ub_g, do_translate=True, no_extrema=False, raw_output=False,
                 debugging=False, logger=None, infeasible_detection=True):
        self.lb_g = lb_g
        self.ub_g = ub_g
        self.dom = dom

        self.do_translate = do_translate
        self.no_extrema = no_extrema
        self.debugging = debugging
        self.raw_output = raw_output

        self.log = logger if logger is not None else self._nop

        if not infeasible_detection:
            self.detect_infeasibility = self._nop

    def ub(self, view):
        var, w = view
        return self.ub_g[var] * w if w > 0 else self.lb_g[var] * w

    def lb(self, view):
        var, w = view
        return self.lb_g[var] * w if w > 0 else self.ub_g[var] * w

    def _nop(self, *args, **kwargs):
        pass

    def detect_infeasibility(self, constraint, dom_override=None):
        """
        Detects infeasible constraints at results in an early termination.
        """
        if not constraint.reified and sum([self.ub(v) for v in constraint.terms]) < constraint.b:
            # self.log("early exit", constraint, type="OE")
            raise EarlyExitException

    def encode(self, constraint, dom_override=None):
        # self.log("encode", constraint, type="OE", lvl=2)

        self.detect_infeasibility(constraint, dom_override=dom_override)

        # if len(constraint.terms) in stats:
        #     stats[len(constraint.terms)] += 1
        # else:
        #     stats[len(constraint.terms)] = 1
        return self._encode((constraint.terms, constraint.b), dom_override=dom_override, reified=constraint.reified)

    def _encode(self, constraint, dom_override=None, reified=None):
        """
        Applies the order encoding to a given constraint in the context of the domains stored in the current instance.
        Domains can be temporary overridden.
        :type constraint: (list[(str, int)], int)
        :type dom_override: dict[str, DomainChunk] | None
        """
        views, c = constraint

        current_view = views[0]
        var, a = current_view

        if dom_override is None:
            dom_override = {}

        # skip_counter = 0

        # stats["call"] += 1

        if len(views) == 1 and a > 0:
            # d_pre_trans = datetime.now()
            clause = [self.translate((False, var, int(math.ceil(float(c) / a))))]
            # d_trans = datetime.now() - d_pre_trans
            # stats["trans"] += d_trans.total_seconds()
            # stats["trans_count"] += 1
            if reified is not None:
                clause.append(reified)
            return [clause]
        elif len(views) == 1 and a < 0:
            # d_pre_trans = datetime.now()
            clause = [self.translate((True, var, c / a + 1))]
            # d_trans = datetime.now() - d_pre_trans
            # stats["trans"] += d_trans.total_seconds()
            # stats["trans_count"] += 1
            if reified is not None:
                clause.append(reified)
            return [clause]
        elif a > 0:
            # stats["a>0"] += 1
            # n >= 2, a > 0
            conjunction = []
            dom = (self.dom[var] if var not in dom_override else dom_override[var])

            # compute the starting point in Dom(var)
            t = (c - sum([self.ub(v) for v in views[1:]])) / a  # minimum value required to satisfy the constraint
            d_start = max(dom.index(t) - 1, 0)

            for d in dom.get_values_asc(start=d_start):
                # stats["for"] += 1
                sub_sum = (views[1:], c - a * d)

                # check whether to exit the loop earlier
                ubs = [self.lb(v) for v in views[1:]]
                if a * d + sum(ubs) >= c:
                    break
                # skip_counter += 1

                sub_enc = self._encode(sub_sum, dom_override=dom_override, reified=reified)

                l, ll = self.translate((False, var, d + 1)), []
                for se in sub_enc:
                    ll.append([l] + se)
                conjunction.extend(ll)
            return conjunction
        else:
            # stats["a<0"] += 1
            # n >= 2, a < 0
            conjunction = []
            dom = (self.dom[var] if var not in dom_override else dom_override[var])

            # compute the starting point in Dom(var)
            t = int((c - sum([self.ub(v) for v in views[1:]])) / a)  # truncate
            idx = -1 if t < dom.lb() else dom.index(t)
            d_start = max(0, len(dom) - (idx + 1) - 1)

            for d in dom.get_values_desc(start=d_start):
                # stats["for"] += 1
                sub_sum = (views[1:], c - a * d)

                # check whether to exit the loop earlier
                ubs = [self.lb(v) for v in views[1:]]
                if a * d + sum(ubs) >= c:
                    break
                # skip_counter += 1

                sub_enc = self._encode(sub_sum, dom_override=dom_override, reified=reified)

                l, ll = self.translate((True, var, d)), []
                for se in sub_enc:
                    ll.append([l] + se)
                conjunction.extend(ll)
            return conjunction

    def translate(self, view):
        if not self.do_translate:
            return view

        signed, var, c = view

        if c <= self.lb_g[var]:
            return var, int(not signed)
        elif c > self.ub_g[var]:
            return var, int(signed)
        else:
            cc, vol = self.next_equal(var, c)

            if self.raw_output:
                return signed, var, (cc if not self.no_extrema else c), c
            else:
                return SignedView(signed, 1, var, '>=', cc, annotation='^' if vol else None)

    def next_equal(self, var, d):
        try:
            v = self.dom[var].search(d)
            return v, False
        except IndexError:
            v = self.dom[var].values[0]
            if v > d and self.lb_g[var] < v and self.dom[var].values[0] > d:
                return -float('inf'), True
            else:
                return float('inf'), True
