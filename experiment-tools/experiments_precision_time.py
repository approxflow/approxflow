import sys, os, re, math
from collections import OrderedDict
import scalmc_driver
import time
from experiments import Result
import matplotlib.pyplot as pyplot
import numpy

try:
  import IPython # for debugging
except:
  pass

options = {}
logfile = sys.stderr

options["use_py33_subprocess"] = True
try:
  sys.path.append("util/subprocess32-py3.3-backport")
except ImportError:
  options["use_py33_subprocess"] = False
options["use_py33_subprocess"] = False # TODO remove this once fixing _posixsubprocess import issues

if options["use_py33_subprocess"]:
  import subprocess32 as subprocess
else:
  import subprocess

DEFAULT_DELTA = 0.2 # 1-0.25 = 0.75 is default tolerance in ApproxMC source code (it's inverted there, listed as delta when really it means 1-delta)
DELTA = "delta"
EPSILON = "epsilon"

results_dict = OrderedDict() # this will be populated by the script, it will map experiment name (filename) to a dictionary, and each of those dictionaries will map tool name to a list of measurements

# Recursively traverse directory structure, adding files to the list
# Or looking for files with a .c extension in each directory
# and subdirectory
# 
# FIXME: doesn't currently handle infinite symlink indirection
def get_files_from_path(arg, acc=OrderedDict(), depth=0):
  if os.path.isdir(arg):
    for path in os.listdir(arg):
      full_path = os.path.join(arg, path)
      if options["depth"] < 0 or (options["depth"] > 0 and depth < options["depth"]):
        if os.path.isdir(full_path):
          get_files_from_path(full_path, acc, depth=depth+1)
        elif os.path.isfile(full_path):
          ext = ".c"
          if options["cnf"]:
            ext = ".cnf"
          split = os.path.basename(path).split(ext)
          if len(split) is 2 and not split[1].strip() and not path[0] is ".":
            assert(full_path not in acc)
            acc[full_path] = True
  elif os.path.isfile(arg):
    assert(arg not in acc)
    acc[arg] = True
  return acc

def run_scalmc(filename, epsilon, delta):
  #(time, out, err) = shell_script(SCALMC, [filename])
  cur_time = time.time()
  (out, err) = scalmc_driver.run_scalmc([filename], epsilon, delta)
  total_time = time.time() - cur_time
  # print("=========")
  # print(out)
  # print("=========")
  # print(err)
  # print("=========")
  
  
  
  timeout = False
  try:
    [multiplier, power] = out.split("Number of solutions is:")[1].split(" x ")
    [base, exponent] = power.split("^")
    multiplier = int(multiplier)
    base = int(base)
    exponent = int(exponent)
    solutions = multiplier * base ** exponent
    info_flow = math.log(solutions, 2)
  except IndexError: # this means there was a timeout or it's unsat
    if "The input formula is unsatisfiable." in out:
      info_flow = "UNSAT"
    else: # timeout, and sadly scalmc doesn't give a partial count
      info_flow = None
      timeout = True
  return (total_time, info_flow, timeout)

def run_exp(exp_filename, epsilon, delta):
  logfile.write("Now running experiment " + exp_filename + " epsilon=" + str(epsilon) + " delta=" + str(delta) + "\n")
  # if options.cnf isn't set, then run CBMC first to generate CNFs then do this
  if exp_filename not in results_dict:
    results_dict[exp_filename] = {}
  if (epsilon, delta) not in results_dict[exp_filename]:
    results_dict[exp_filename][(epsilon, delta)] = []
  if options["cnf"]:
    logfile.write("    Running scalmc... ")
    # run scalmc
    (time, info_flow, timeout) = run_scalmc(exp_filename, epsilon, delta)
    scalmc_result = Result(time, info_flow, exp_filename, timeout)
    logfile.write("done: " + str(scalmc_result) + "\n")
    results_dict[exp_filename][(epsilon, delta)].append(scalmc_result)
    
    # if all the observations are empty, then this experiment failed for some reason, so remove it? or put a special value here
    empty = True
    for (e, d) in results_dict[exp_filename]:
      if len(results_dict[exp_filename][(e, d)]) > 0:
        empty = False
        break
    if empty:
      del results_dict[exp_filename] # or put a special value instead?


def main(argv):
  # Deal with program arguments
  def usage():
    print("Usage: " + argv[0] + " experiment-list [depth=n] [cnf=true/false]")
    print("      experiment: a mixed list of files and directories, looks for .c files inside each directory specified")
    print("           depth: maximum directory depth to recurse, \"no limit\" if negative value, \"max\", or \"inf\" is passed, no recursion if 0 is passed (default: 8)" )
    print("           cnf: CNF mode -- will perform only model counting (default: true), valid modes: (false, f, 0)" )
    print("           runs: The integer number of times to run the tools on each experiment (default: 1)")
    print("           timeout: The timeout for each experiment, in an integral number of seconds -- no timeout if omitted (default: no timeout)")
    
  if len(argv) < 2:
    usage()
    exit(1)
  
  global options
  # Maps each keyword argument to a function that converts the argument to a python value of the appropriate type
  kwarg_type_converters = \
    {"depth":
          lambda v: int(v) if v.lower() not in ["inf", "max"] and int(v) > 0 else -1,
     "cnf":
          lambda v: v.lower() not in ["f", "false", "0"],
     "timeout":
          lambda v: int(float(v)) if round(float(v)) == int(float(v)) and int(float(v)) > 0 else None,
     "runs":
          lambda v: int(v) if int(v) > 1 else 1}
  kwargs={"depth": 8, "cnf": True} # default values
  posargs = []
  for arg in argv:
    is_kwarg = False
    for kwarg in kwarg_type_converters:
      if arg.lower().startswith(kwarg + "="):
        is_kwarg = True
    if not is_kwarg:
      posargs.append(arg)
    else:
      split = arg.lower().split("=")
      kwargs[split[0]] = kwarg_type_converters[split[0]]((split[1]))
  
  if len(posargs) < 2:
    usage()
    exit(1)
  
  options = kwargs
  # Resolve the list of experiments
  
  ext = ".c"
  if options["cnf"]:
    ext = "cnf"
  files = get_files_from_path(posargs[1])
  for arg in posargs[2:]:
    files.update(get_files_from_path(arg))
  
  if "timeout" not in options:
    options["timeout"] = None
  
  if "runs" not in options:
    options["runs"] = 1
  #print(files)
  #print(len(files))
  
  # Now the main program, run these experiments
  step = 0.05
  epsilon_range = reversed([j*step for j in range(1, int(1.0/step)+1, 1)])
  #delta_range = [j*step for j in range(1, int(1.0/step)+1, 1)]
  #DEFAULT_DELTA = None
  delta_range = [DEFAULT_DELTA]
  
  for exp in files:
    for i in xrange(options["runs"]):
      for epsilon in epsilon_range:
        for delta in delta_range:
          run_exp(exp, epsilon, delta)
  
  # Now output the results
  print("+++++++++++++++++++++++++")
  print("+++++++++++++++++++++++++")
  print("+++++++++++++++++++++++++")
  print("+++++    RESULTS    +++++")
  print("+++++++++++++++++++++++++")
  print("+++++++++++++++++++++++++")
  print("+++++++++++++++++++++++++")
  print("")
  
  for exp in results_dict:
    print("\nExperiment " + exp + ":")
    for (epsilon, delta) in results_dict[exp]:
      print("    Results for epsilon=" + str(epsilon) + " delta=" + str(delta) + ":")
      for result in results_dict[exp][(epsilon, delta)]:
        print("        " + str(result))
  sys.stdout.flush()
  
  
  # TODO: assumes single entry, not a big deal to loop through each exp though...
  # TODO: assumes single measurement for each -- if more needed in the future, do the statistics BEFORE, and put it in the variable called results (i.e. if want median replace list of >1 Result obj with a list containing a single Result obj that represents the median)
  
  # generate new results after taking the time-average
  
  results = results_dict[list(results_dict)[0]]
  x = [i for (i, j) in results if j == DEFAULT_DELTA]
  
  #y = [results[(i,j)][0].time for (i, j) in results if j == DEFAULT_DELTA] # assumes only a single observation
  y = [numpy.mean([result.time for result in results[(i,j)]]) for (i,j) in results if j == DEFAULT_DELTA]
  
  pyplot.plot(x,y)
  pyplot.savefig("tmp/plot.png")
  #pyplot.show()
  
  for (epsilon, delta) in sorted(results):
    if delta == DEFAULT_DELTA:
      print("e=%.2f d=%.2f: %.4f" % (float(epsilon), float(delta), float(results[(epsilon, delta)][0].time)))
  
  

if __name__ == "__main__":
  main(sys.argv)