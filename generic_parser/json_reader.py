import json
import gzip
import sys
from time import time
from order_encoding.constraint import Constraint
from domains.continuous.continuous_domain import ContinuousDomain
from domains.domain_by_enum import DomainByEnum
from domains.domain_by_monotonic_function import DomainByMonotonicFunction


def read(file_path, logger, t_start=None):
    if t_start is None:
        t_start = time()

    if file_path != sys.stdin:
        if file_path[-3:] == '.gz':
            with gzip.open(file_path, 'r') as inst:
                instance = json.load(inst)
        else:
            with open(file_path, "r") as inst:
                instance = json.load(inst)
    else:
        instance = json.loads(file_path.read())

    logger("json read", type="time")

    # boolean
    booleans = [str(b) for b in instance["booleans"]]

    # clauses
    clauses = []
    for c in instance["clauses"]:
        clauses.append(map(str, c))

    # bool2int
    bool2int = []
    for b in instance["bool_to_int"]:
        bool2int.append(tuple(map(str, b)))

    # restore domain classes
    domains = {}
    for var, class_info in instance['bounds'].items():
        class_str, class_args = class_info
        domains[str(var)] = eval(class_str)(*class_args)

    logger("domains parsed", type="time")

    # constraints
    constraints = []
    instance['constraints'] = map(lambda c: tuple(c), instance['constraints'])
    raw_constraints = []
    for cc in instance['constraints']:
        c = (map(lambda x: (str(x[0]), x[1]), cc[0]), cc[1], str(cc[2]) if cc[2] is not None else None)
        raw_constraints.append(c)
    for terms, b, r in raw_constraints:
        constraints.append(Constraint([tuple(term) for term in terms], b, reified=r))

    logger("constraints parsed", type="time")

    # optimization
    opt = {}
    for var, o in instance["opt_vector"]:
        opt[str(var)] = o

    logger("opt vector parsed", type="time")

    return booleans, clauses, bool2int, domains, constraints, opt
