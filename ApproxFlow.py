#!/usr/bin/python
# Imports and path resolutions, etc.
###########################################

# for storing program options
from pathlib import Path


class OptionsDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as e:
            raise AttributeError(e)

    def __setattr__(self, key, value):
        self[key] = value


options = OptionsDict()

import re

import sys

sys.path.append("util")

options.use_py33_subprocess = True
try:
    sys.path.append("util/subprocess32-py3.3-backport")
except ImportError:
    options.use_py33_subprocess = False
options.use_py33_subprocess = False  # TODO remove this once fixing _posixsubprocess import issues

if options.use_py33_subprocess:
    import subprocess32 as subprocess
else:
    import subprocess

import math, os

sys.path.append(os.path.abspath("util"))
sys.path.append("util/cnftools")
import cnftools_rename


# End of imports and path resolutions, etc.
###########################################

# for printing options
class VerbosityLevelsDict(dict):
    limit_dict = {"verbosity_max": False, "verbosity_min": False}

    def __getattr__(self, key):
        if key in self.limit_dict:
            return self.limit_dict[key]
        elif self.limit_dict["verbosity_max"] and not self.limit_dict["verbosity_min"]:
            return True
        elif self.limit_dict["verbosity_min"] and not self.limit_dict["verbosity_max"]:
            return False
        else:
            return self.key

    def __setattr__(self, key, value):
        if type(value) is not bool:
            raise ValueError("value " + str(value) + " to be added to verbosity dict is not of type bool")
        elif key == "verbosity_max":
            self.limit_dict["verbosity_max"] = value
        elif key == "verbosity_min":
            self.limit_dict["verbosity_min"] = value
        else:
            self[key] = value


# printing options

options.verbosity = VerbosityLevelsDict()
options.verbosity.verbosity_max = True  # overrides all others, others may be false only if this is false
options.verbosity.verbosity_min = False  # overrides all others, others may be false only if this is false
options.verbosity.print_cbmc_out = True
options.verbosity.print_cbmc_err = True
options.verbosity.print_modelcounter_out = True
options.verbosity.print_modelcounter_err = True

APPROX_MC = "c ind"
APPROX_MC_PY = "cr"
SHARPCDCL = "scope"


# noinspection PyUnusedLocal
def decide_info_flow(klass, classpath, cnf_only, int_sz=-1, modelcounter_timeout=None):
    wrote_in_allsat_var_projection_scope = {APPROX_MC: set(), APPROX_MC_PY: set(), SHARPCDCL: set()}

    # tmp_cnf_filename = tmpdir + "/TEMP.cnf"

    print("We're starting our info flow measurement.")
    if type(modelcounter_timeout) in [int, float]:
        modelcounter_timeout = int(round(float(modelcounter_timeout) / 1000))  # convert to seconds from millis
    print("We got the variable size: " + str(int_sz))

    re_to_match = re.compile("(___val)#[0-9]+")
    # re_to_match_whole_line = re.compile("\s*c\s*[a-zA-Z_0-9]+::[0-9]+::(__return_value)![0-9]+@[0-9]+#[0-9]+")
    # tmp_cnf_filename_template_re = re.compile("\s*c\s*[a-bA-Z_0-9]+::[0-9]+::(__return_value)![0-9]+@[0-9]+#[0-9]+")
    print("We're about to try running cbmc")
    tmp_cnf_filename = classpath + "/" + klass + ".cnf"
    # Generate a CNF with JBMC
    args = [klass, "--classpath",
            os.path.abspath(os.path.dirname(__file__)) + "/jbmc-core-models.jar:" + str(Path(classpath).absolute()), "--dimacs"]
    # args = [filename, "--" + str(int_sz), "--function", fn, "--dimacs", "--unwind", str(unwind_limit)]
    # args = [filename, "--" + str(int_sz), "--function", fn, "--dimacs", "--slice-formula", "--ignore-nonauto-assertions", "--print-assertion-literals", "--unwind", str(unwind_limit)] # ah right, vanilla cbmc doesn't have "--ignore-nonauto-assertions", "--print-assertion-literals", or "--havoc"
    # if use_havoc:
    # args.append("--havoc")
    args.extend(["--outfile", os.path.abspath(tmp_cnf_filename)])
    if os.getenv("PARTIAL_LOOPS", "false") != "false":
        args.extend(["--partial-loops"])
    if os.getenv("NO_UNWIND", "false") == "false":
        args.extend(["--unwind", os.getenv("UNWIND", "32")])
    print("We're about to try running jbmc with the following args:")
    print(" ".join(args))
    subprocess.check_call("cd {}; jbmc {}".format(classpath, " ".join(args)), shell=True)

    print("We got our CNF: ")

    # We have our CNF - now it's time to run allsat on it and gather learned
    # clauses

    # first, we need to know which variables to do allsat on:

    # noinspection PyShadowingNames
    def get_allsat_vars(cnffile):
        # search for __return_value!i@j#k, and assume only k changes (should be true if there's only a single function converted to single return point named __return_value
        (i, j, k) = (None, None, -1)
        max_lits = None
        for line in cnffile:
            if line.startswith("c"):
                match = re_to_match.search(line)
                if match:
                    assert (len(match.groups()) == 1)
                    m = match.group(0).split("___val")[1]
                    assert (i is None or i == int(m.split("@")[0]))
                    assert (j is None or j == int(m.split("#")[0].split("@")[1]))
                    new_k = int(m.split("#")[1])
                    if new_k > k:
                        k = new_k
                        max_lits = [int(var) for var in line.split()[2:] if var.lower() not in ["true", "false"]]
        # apparently, CBMC can report duplicate entries here?? Or is it a bug somewhere in my toolchain? [but where, I'm not using any cnftools etc before this point...] -- so, just make it unique
        if max_lits:
            return list(set(max_lits))  # order shouldn't matter so just turn it into a set then into a list again

    if cnf_only:
        print("cnf-only argument is set, skipping model counting, cnf is " + tmp_cnf_filename)

    with open(tmp_cnf_filename, "r") as cnffile:
        allsat_vars = get_allsat_vars(cnffile)

    if not allsat_vars:  # if None or empty
        print(
            "warning: did not receive literals on which to do #sat from cbmc procedure, maybe it was simplified out? skipping #sat solving")
        print("a reason for this might be that the leakage is 0")
        # print "fatal error: did not receive literals on which to do #sat from cbmc procedure, quitting before doing #sat solving"
        exit(1)
    rename_to_lits = range(1, len(allsat_vars) + 1)
    cnftools_rename.rename_literals(tmp_cnf_filename, allsat_vars, rename_to_lits)
    allsat_vars = rename_to_lits

    # now we have to run the approximate #SAT

    # check if scope lines already exist
    with open(tmp_cnf_filename, "r") as cnffile:
        for line in cnffile:
            if line.startswith(APPROX_MC):
                lits = [int(e.strip()) for e in line.split(APPROX_MC)[1].split() if int(e.strip()) != 0]
                for l in lits:
                    wrote_in_allsat_var_projection_scope[APPROX_MC].add(l)
            if line.startswith(APPROX_MC_PY):
                lits = [int(e.strip()) for e in line.split(APPROX_MC_PY)[1].split() if int(e.strip()) != 0]
                for l in lits:
                    wrote_in_allsat_var_projection_scope[APPROX_MC_PY].add(l)
    try:
        with open(tmp_cnf_filename + ".scope", "r") as scopefile:
            lits = [int(e.strip()) for e in scopefile.readlines()]
            for l in lits:
                wrote_in_allsat_var_projection_scope[SHARPCDCL].add(l)
    except:
        pass
    # first, add the c ind lines for scalmc
    with open(tmp_cnf_filename, "a") as cnffile:
        i = 0
        approxmc_allsat_vars = [e for e in allsat_vars if e not in wrote_in_allsat_var_projection_scope[APPROX_MC]]
        while i < len(approxmc_allsat_vars):
            tokens = approxmc_allsat_vars[i:i + 10]
            if len(tokens) > 0:
                print("c ind " + " ".join([str(v) for v in tokens]) + " 0")
                cnffile.write("c ind " + " ".join([str(v) for v in tokens]) + " 0\n")
            for l in tokens:
                wrote_in_allsat_var_projection_scope[APPROX_MC].add(l)
            i += 10
        approxmc_py_allsat_vars = [e for e in allsat_vars if
                                   e not in wrote_in_allsat_var_projection_scope[APPROX_MC_PY]]
        if len(approxmc_py_allsat_vars) > 0:
            print("cr " + " ".join([str(v) for v in approxmc_py_allsat_vars]))
            cnffile.write("cr " + " ".join([str(v) for v in approxmc_py_allsat_vars]) + "\n")
        for l in approxmc_py_allsat_vars:
            wrote_in_allsat_var_projection_scope[APPROX_MC_PY].add(l)
    if len(wrote_in_allsat_var_projection_scope[SHARPCDCL]) == 0:
        with open(tmp_cnf_filename + ".scope", "w+") as scopefile:
            sharpcdcl_allsat_vars = [e for e in allsat_vars if e not in wrote_in_allsat_var_projection_scope[SHARPCDCL]]
            scopefile.write("\n".join([str(v) for v in sharpcdcl_allsat_vars]))
            for l in sharpcdcl_allsat_vars:
                wrote_in_allsat_var_projection_scope[SHARPCDCL].add(l)

    if not cnf_only:
        # now run the program
        args = [tmp_cnf_filename]
        p = subprocess.Popen([os.path.join(os.path.dirname(__file__), "util/scalmc")] + args,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # if using the py3.3 subprocess backport, we have timeout available
        if modelcounter_timeout is not None:
            try:
                out, err = p.communicate()
            except subprocess.TimeoutExpired:
                p.kill()
                out, err = p.communicate()
        else:
            out, err = p.communicate()
        if options.verbosity.print_modelcounter_out:
            print(out.decode())
        if options.verbosity.print_modelcounter_err:
            print(err.decode())
        [multiplier, power] = out.decode().split("Number of solutions is:")[1].split(" x ")
        [base, exponent] = power.split("^")
        multiplier = int(multiplier)
        base = int(base)
        exponent = int(exponent)
        solutions = multiplier * base ** exponent
        info_flow = math.log(solutions, 2)
        print("Approximated flow is: {}".format(info_flow))


def build_class(klass, classpath):
    subprocess.check_call("cd {}; javac {}.java -cp {}/jbmc-core-models.jar".format(classpath, klass, os.path.abspath(os.path.dirname(__file__))), shell=True)


def main(argv):
    klass = argv[1]
    classpath = argv[2]
    cnf_only = os.getenv("CNF_ONLY", "") != ""
    build_class(klass, classpath)
    decide_info_flow(klass, classpath, cnf_only,
                     modelcounter_timeout=1000)


if __name__ == "__main__":
    def usage_and_exit():
        print("usage: " + sys.argv[0] + " class classpath")
        print("     class: main class that is placed in the default package")
        print(" classpath: classpath with a main class that has a static ___val variable for output")
        print(" use env variable declaration CNF_ONLY=1 to create only CNF file")
        exit(1)


    if len(sys.argv) < 2:
        usage_and_exit()

    main(sys.argv)
