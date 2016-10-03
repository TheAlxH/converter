import json
import sys
from OutputWriter import OutputWriter


class IncWriter(OutputWriter):
    def __init__(self, **options):
        super(IncWriter, self).__init__(**options)
        self.instance = {}

    def write(self, output, int_variables_with_bounds, bool_vars, opt_vector, constraints, clauses, b2i):
        if not output:
            raise Exception('no output filename specified')

        self.write_opt_vector(opt_vector)
        self.write_constraints(constraints)
        self.write_bounds(int_variables_with_bounds)
        self.write_bool_variables(bool_vars)
        self.write_clauses(clauses)
        self.write_b2i(b2i)

        if output == sys.stdout:
            print json.dumps(self.instance)
        else:
            with open(output + '.json', 'w') as outfile:
                json.dump(self.instance, outfile)

    def write_opt_vector(self, opt_vector):
        """
        :type opt_vector: list[(str, int)]
        """
        self.instance['opt_vector'] = opt_vector

    def write_constraints(self, constraints):
        """
        :type constraints: list[(list[(str, int)], int)]
        """
        self.instance['constraints'] = constraints

    def write_bounds(self, bounds):
        """
        :type bounds: dict[str, ContinuousDomain]
        """
        # TODO all domain classes!!!
        self.instance['bounds'] = {var: dom.export_self() for var, dom in bounds.items()}

    def write_bool_variables(self, variables):
        self.instance['booleans'] = [var for var in variables]

    def write_clauses(self, clauses):
        self.instance['clauses'] = clauses

    def write_b2i(self, b2i):
        self.instance['bool_to_int'] = b2i
