"""
@author: Tino Prahl
@author: Alexander Haeusler
"""

import re
from sys import maxint
import gzip
import sys


class Parser(object):
    def __init__(self):
        self.symbol = "[A-Za-z0-9_@#\.\-\(\)]"
        self.vars = []
        self.name = ""
        self.minimize = True
        self.rel = {}
        self.opt = {}
        self.cond = {}
        self.rhs = {}
        self.lo = {}
        self.up = {}
        self.freeLo = {}
        self.cspMap = {}
        self.convert_float = False

    def cleanup(self):
        self.vars = []
        self.name = ""
        self.minimize = True
        self.rel = {}
        self.opt = {}
        self.cond = {}
        self.rhs = {}
        self.lo = {}
        self.up = {}
        self.freeLo = {}
        self.cspMap = {}

    def _init_mps(self):
        self.patName = re.compile('NAME\s+(%s+)' % self.symbol)
        self.patRows = re.compile('ROWS(.+?)COLUMNS', re.DOTALL)
        self.patRel = re.compile('({0}+)\s+({0}+)'.format(self.symbol))
        self.patCols = re.compile('COLUMNS(.+?)(RHS|RANGES|BOUNDS|ENDATA)', re.DOTALL)
        self.patVars = re.compile('(%s+) +(.+ [\-0-9\.]+)' % self.symbol)
        self.patCond = re.compile('(%s+) +([\-0-9\.]+)' % self.symbol)

        # ##

        self.patRHS = re.compile('RHS(.+?)(BOUNDS|RANGES|ENDATA)', re.DOTALL)
        self.patBounds = re.compile('BOUNDS(.+?)(RHS|RANGES|ENDATA)', re.DOTALL)
        self.patType = re.compile('({0}{0}) +({0}+) +({0}+) *([\-0-9\.]*)'.format(self.symbol))

    # read MPS-files
    def parse_mps(self, path, is_gzipped=False):
        self.cleanup()
        self._init_mps()

        if path != sys.stdin and not is_gzipped:
            f = open(path, "r")
        elif type(path) == str:
            f = gzip.open(path, "r")
        else:
            f = path

        text = f.read()
        f.close()

        # find name
        self.name = self.patName.findall(text)
        l = len(self.name)
        if l == 1:
            self.name = self.name[0]
        elif l == 0:
            self.name = ""
        else:
            print "found more than one name"
            for i in self.name:
                print i
            exit(-1)

        # find block with rows
        rows = self.patRows.findall(text)
        l = len(rows)
        if l == 1:
            rows = rows[0]
        elif l == 0:
            self._error("Can not find ROWS")
        else:
            self._error("found %d blocks with rows" % l)

        # get all relations
        for i in self.patRel.finditer(rows):
            if "N" == i.group(1):
                if self.opt == {}:
                    self.opt.update({i.group(2): {}})
                else:
                    self._error("multiple optimization-functions\n%s\n%s" % (str(self.opt), i.group(2)))
            elif i.group(1) in ["E", "G", "L"]:
                if i.group(2) in self.rel:
                    self._error("double entry in ROWS\n%s" % i.group(2))
                else:
                    self.rel.update({i.group(2): i.group(1)})
            else:
                print "unknown relation"
                print i.group(1)
                exit(-1)
        if self.opt == "": self._error("missing optimization-function")
        del rows

        # find block with columns
        cols = self.patCols.findall(text)
        l = len(cols)
        if l == 1:
            cols = cols[0][0]
        elif l == 0:
            self._error("Can not find COLS")
        else:
            self._error("found %d blocks with columns" % l)

        # get all conditions
        for i in self.patVars.finditer(cols):
            if not i.group(1) in self.vars: self.vars.append(i.group(1))
            for j in self.patCond.finditer(i.group(2)):
                z = self._toInt(j.group(2))
                if j.group(1) in self.opt:
                    pointer = self.opt[j.group(1)]
                    if i.group(1) in pointer:
                        self._error("Double Entry in Conditions:\nVar: %s\nCond: %s" % (i.group(1), j.group(1)))
                    else:
                        pointer.update({i.group(1): z})
                else:
                    if not j.group(1) in self.rel: self._error("%s in COLUMNS is not defined in ROWS" % j.group(1))
                    if j.group(1) in self.cond:
                        pointer = self.cond[j.group(1)]
                        if i.group(1) in pointer:
                            self._error("Double Entry in Conditions:\nVar: %s\nCond: %s" % (i.group(1), j.group(1)))
                        else:
                            pointer.update({i.group(1): z})
                    else:
                        self.cond.update({j.group(1): {i.group(1): z}})
        del cols

        # get Right-Hand-Side
        rhs = self.patRHS.findall(text)
        l = len(rhs)
        if l == 1:
            rhs = rhs[0][0]
        elif l == 0:
            rhs = ""
        else:
            self._error("found %d blocks with RHS" % l)
        for i in self.patVars.finditer(rhs):
            for j in self.patCond.finditer(i.group(2)):
                if not j.group(1) in self.rel: self._error("%s in RHS is not defined in ROWS" % j.group(1))
                if j.group(1) in self.rhs:
                    self._error("Double Entry in RHS:\nRHS: %s\nCond: %s" % (i.group(1), j.group(1)))
                else:
                    z = self._toInt(j.group(2))
                    self.rhs.update({j.group(1): z})
        del rhs

        bounds = self.patBounds.findall(text)
        l = len(bounds)
        if l == 1:
            bounds = bounds[0][0]
        elif l == 0:
            bounds = ""
        else:
            self._error("found %d blocks with BOUNDS" % l)
        for i in self.patType.finditer(bounds):
            if not i.group(3) in self.vars: self.vars.append(i.group(3))
            if i.group(1) in ["UP", "UI", "SC"]:
                if i.group(3) in self.up:
                    self._error("Double Entry in BOUNDS:\nBOUND: %s %s\nVar: %s" % (i.group(1), i.group(2), i.group(3)))
                z = self._toInt(i.group(4))
                self.up.update({i.group(3): z})
            elif i.group(1) in ["LO", "LI"]:
                if i.group(3) in self.lo:
                    self._error("Double Entry in BOUNDS:\nBOUND: %s %s\nVar: %s" % (i.group(1), i.group(2), i.group(3)))
                z = self._toInt(i.group(4))
                self.lo.update({i.group(3): z})
            elif i.group(1) in ["BV"]:
                if i.group(3) in self.up:
                    self._error("Double Entry in BOUNDS:\nBOUND: %s %s\nVar: %s" % (i.group(1), i.group(2), i.group(3)))
                if i.group(3) in self.lo:
                    self._error("Double Entry in BOUNDS:\nBOUND: %s %s\nVar: %s" % (i.group(1), i.group(2), i.group(3)))
                self.lo.update({i.group(3): 0})
                self.up.update({i.group(3): 1})
            elif i.group(1) in ["FX"]:
                if i.group(3) in self.up:
                    self._error("Double Entry in BOUNDS:\nBOUND: %s %s\nVar: %s" % (i.group(1), i.group(2), i.group(3)))
                if i.group(3) in self.lo:
                    self._error("Double Entry in BOUNDS:\nBOUND: %s %s\nVar: %s" % (i.group(1), i.group(2), i.group(3)))
                z = self._toInt(i.group(4))
                self.lo.update({i.group(3): z})
                self.up.update({i.group(3): z})
            elif i.group(1) in ["FR", "MI"]:
                self.freeLo.update({i.group(3): i.group(2)})
        del bounds
        self._checkFree()

    def toCPLEXLP(self, path):
        f = open(path, 'w')
        f.write("\\Name: %s\n" % self.name)
        if self.minimize:
            f.write("Minimize")
        else:
            f.write("Maximize")
        for i, pointer in self.opt.iteritems():
            f.write("\n %s:" % i)
            for j in pointer:
                f.write(" %d %s" % (pointer[j], j))
        f.write("\nSubject To")
        for i, pointer in self.cond.iteritems():
            f.write("\n %s:" % i)
            for j in pointer:
                f.write(" %d %s" % (pointer[j], j))
            s = self.rel[i]
            if s == "G":
                f.write(" >=")
            elif s == "L":
                f.write(" <=")
            elif s == "E":
                f.write(" =")
            if i in self.rhs:
                f.write(" %d" % self.rhs[i])
            else:
                f.write(" 0")
        f.write("\nBounds")
        for i in self.vars:
            if i in self.lo or i in self.up or i in self.freeLo:
                f.write("\n")
                if i in self.lo:
                    f.write(" %d <=" % self.lo[i])
                elif i in self.freeLo:
                    f.write(" -inf <=")
                f.write(" %s" % i)
                if i in self.up:
                    f.write(" <= %d" % self.up[i])
        f.write("\nGeneral")
        for i in self.vars:
            f.write("\n %s" % i)
        f.write("\nEnd")
        f.close()

    def to_asp(self, path):
        f = open(path, 'w')
        f.write("%% Name: %s \n" % self.name)
        if self.minimize:
            f.write("minimize.\n\n")
        else:
            f.write("maximize.\n\n")
        f.write("%% Name: %s \n" % self.name)
        for i, j in self.opt.iteritems():
            f.write("%% Optimization: %s\n" % i)
            for x, y in j.iteritems():
                f.write(' c("%s",%d).' % (x, y))
        f.write("\n\n%Conditions\n")
        row = 1
        for key, cond in self.cond.iteritems():
            b = self.rel[key]
            if b == 'E':
                name = {key + '_E_G': 1, key + '_E_L': -1}
            elif b == 'G':
                name = {key: 1}
            elif b == 'L':
                name = {key: -1}
            try:
                rhs = self.rhs[key]
            except:
                rhs = 0
            for n, m in name.iteritems():
                f.write("%% %s\n order(%d,start," % (n, row))
                for j in self.vars:
                    if j in cond:
                        f.write('(%d,"%s")). order(%d,"%s",' % (m * cond[j], j, row, j))
                f.write('end). b(%d,%d).\n' % (row, m * rhs))
                row += 1
        f.write("\n")
        f.write("%Bounds\n")
        temp = 'l("%s",%d).\n'
        for i, j in self.lo.iteritems():
            f.write(temp % (i, j))
        temp = 'u("%s",%d).\n'
        for i, j in self.up.iteritems():
            f.write(temp % (i, j))
        f.close()

    def to_csp(self, path):
        f = open(path, 'w')
        f.write("; Name: %s \n\n" % self.name)
        min_obj = 0
        max_obj = 0
        for i in self.vars:
            if i in self.lo and i in self.up:
                f.write("(int %s %d %d)\n" % (self._csp_replace(i), self.lo[i], self.up[i]))
                for optName, j in self.opt.iteritems():
                    if i in j:
                        if j[i] > 0:
                            min_obj += j[i] * self.lo[i]
                            max_obj += j[i] * self.up[i]
                        else:
                            min_obj += j[i] * self.up[i]
                            max_obj += j[i] * self.lo[i]
        f.write("(int obj %d %d)\n" % (min_obj, max_obj))

        f.write("\n\n; Conditions\n")
        for key, cond in self.cond.iteritems():
            f.write("; %s\n" % key)
            try:
                rhs = self.rhs[key]
            except:
                rhs = 0
            rel = self.rel[key]
            if rel == 'E':
                f.write("(eq (+")
            elif rel == 'G':
                f.write("(ge (+")
            elif rel == 'L':
                f.write("(le (+")
            for i, j in cond.iteritems():
                f.write(" (* %d %s)" % (j, self._csp_replace(i)))
            f.write(") %d)\n" % rhs)

        for optName, i in self.opt.iteritems():
            f.write("\n; Optimization: %s\n(eq (+" % optName)
            for x, y in i.iteritems():
                f.write(" (* %d %s)" % (y, self._csp_replace(x)))
            f.write(") obj)\n")
        if self.minimize:
            f.write("(objective minimize obj )\n")
        else:
            f.write("(objective maximize obj )\n")
        f.write("\n; END")
        f.close()
        f = open(path + ".map", 'w')
        for r, s in self.cspMap.iteritems():
            f.write("%s\t-->\t%s\n" % (r, s))
        f.close()

    def _csp_replace(self, s):
        # ,"@",".","(",")"
        unknown = ["#", "@", "(", ")"]
        r = s
        for i in unknown:
            r = r.replace(i, "_")
        if r != s:
            self.cspMap.update({r: s})
        return r

    def set_bounds(self):
        # set lower bounds to 0
        for i in self.vars:
            if not i in self.lo and not i in self.freeLo:
                self.lo.update({i: 0})

        # build up a copy of conditions and get rhs/rel
        pre_calc = {}
        rhs = {}
        for i, j in self.cond.iteritems():
            for u in j:
                if not u in self.up:
                    r = self.rel[i]
                    if r == "E":
                        name = {i + " E G": 1, i + " E L": -1}
                    elif r == "G":
                        name = {i + " G": 1}
                    elif r == "L":
                        name = {i + " L": -1}
                    for n, m in name.iteritems():
                        if m * j[u] < 0:
                            pre_calc.update({n: {key: m * val for key, val in j.iteritems()}})
                            if i in self.rhs:
                                rhs.update({n: m * self.rhs[i]})
                            else:
                                rhs.update({n: 0})
        # try to set bounds
        changed = 1
        while changed:
            delete = {}
            for name, i in pre_calc.iteritems():
                delete.update({name: []})
                for m, n in i.iteritems():
                    if n == 0:
                        delete[name].append(m)
                    elif m in self.up:
                        if n > 0:
                            rhs[name] -= n * self.up[m]
                            delete[name].append(m)
                        elif m in self.lo:
                            rhs[name] -= n * self.lo[m]
                            delete[name].append(m)

            changed = 0
            for name, d in delete.iteritems():
                for i in d:
                    del pre_calc[name][i]
                    changed = 1
                if pre_calc[name] == {}:
                    del pre_calc[name]

            for name, i in pre_calc.iteritems():
                if [key for key, val in i.iteritems() if val > 0] == []:
                    for key, val in i.iteritems():
                        z = rhs[name] / val
                        if key in self.up:
                            if z < self.up[key]:
                                self.up[key] = z
                        else:
                            self.up.update({key: z})
                        changed = 1
        if pre_calc != {}:
            print "Could not resolve all..."

    def sort_vars(self):
        self.vars.sort(key=self._keyDiff)

    def _keyDiff(self, var):
        if var in self.up and var in self.lo:
            return self.up[var] - self.lo[var]
        else:
            return maxint

    def _checkFree(self):
        for i in self.lo:
            if i in self.freeLo:
                del self.freeLo[i]

    def _error(self, error):
        print error
        exit(-1)

    def _toInt(self, s):
        try:
            f = float(s)
            z = int(f)
        except:
            print "Can not convert '%s' to integer." % s
            exit(-1)
        if not self.convert_float and float(z) != f:
            print "'%s' has a floating value." % s
            exit(-1)
        return z