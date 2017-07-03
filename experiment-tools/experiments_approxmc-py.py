import sys, os, re, math
from collections import OrderedDict

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

# Experimental result
class Result:
  def __init__(self, time=None, info_flow=None, name=None, timeout=False):
    self.info_flow = info_flow
    self.time = time
    self.name = name
    self.timeout = timeout
  
  def __repr__(self):
    #return(self.__class__.__name__ + "(info_flow=" + str(self.info_flow) + ", time=" + str(self.time) + ", name=" + str(self.name) + ", timeout=" + str(self.timeout) + ")")
    return(self.__class__.__name__ + "(info_flow=" + str(self.info_flow) + ", time=" + str(self.time) + ", name=" + str(self.name) + ", timeout=" + str(self.timeout) + ")")
  __str__ = __repr__
  def __hash__(self):
    return hash((self.info_flow, self.time, self.name, self.timeout))

SCALMC = "approxmc-p.py"
SHARPCDCL = "sharpCDCL"

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

# execute a shell script
def shell_script(prog, args, shell=False):
  time_re = re.compile("real\s+[0-9]*\.[0-9]+$")
  timeout_strlist = []
  if options["timeout"]:
    timeout_strlist = ["timeout", str(options["timeout"]) + "s"]
  if shell:
    p = subprocess.Popen(["/bin/bash -c \"" + " ".join(["time", "-p"] + timeout_strlist + [prog] + args) + "\""], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  else:
    p = subprocess.Popen(["time", "-p"] + timeout_strlist + [prog] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  (out, err) = p.communicate()
  err_lines = err.split("\n")
  time_line = err_lines[-4]
  time = float(time_line.split()[1])
  assert(time_re.match(time_line))
  err = "\n".join(err_lines[:-5]) # strip out the 5 lines added by time # FIXME: the non-zero exit code line (err_lines[-5] may be added by something else, not time)
  return (time, out, err)

def run_scalmc(filename):
  tolerance = "0.8"
  confidence = "0.8"
  (_, out, err) = shell_script("which", [SCALMC])
  approxmc_basedir = os.path.dirname(out.strip())
  cryptominisat_driver = os.path.join(approxmc_basedir, "adapters", "cryptominisat4.sh")
  args = ["-vvvv", "-t", tolerance, "-c", confidence, "--sat-command", "'" + cryptominisat_driver, "{maxcount}", "{file}'", filename]
  (time, out, err) = shell_script(SCALMC, args, shell=True)
  #if "binsearch.32.c_main.cnf" in filename:
  #  IPython.embed()
  timeout = False
  try:
    solutions = int(out.split("Model-Count:")[1].strip())
    info_flow = math.log(solutions, 2)
  except (IndexError, ValueError): # this means there was a timeout or it's unsat
    if "The input formula is unsatisfiable." in out:
      info_flow = "UNSAT"
    else: # timeout, and sadly scalmc doesn't give a partial count
      try:
        if solutions == 0:
          info_flow = "ERROR"
      except: # timeout, and sadly scalmc doesn't give a partial count
        info_flow = None
        timeout = True
  return (time, info_flow, timeout)

def run_sharpCDCL(filename, scope_filename=None):
  #return (0, "DIDN'T RUN", False)
  #time_re = re.compile("real\s+[0-9]*\.[0-9]+$")
  timed_out_re = re.compile("^\s*Found Models:\s+[0-9]+\s+UNTIL\s+being\s+interrupted\s*$")
  timeout = False
  if scope_filename is None:
    scope_filename = filename + ".scope"
  args = ["-countMode=2", filename]
  args = ["-countMode=2", "-projection=" + scope_filename, filename]
  (time, out, err) = shell_script(SHARPCDCL, args)
  #if "binsearch.32.c_main.cnf" in filename:
  #  IPython.embed()
  if err and timed_out_re.search(err):
    timeout = True
  try:
    solutions = int(out.split("\n")[-2].strip())
    info_flow = math.log(solutions, 2)
  except ValueError: #unsat
    if "INDETERMINATE" in out or "INDETERMINATE" in err or "INDET" in out or "INDET" in err:
      info_flow = "INDET"
    else:
      info_flow = "ERROR"
  except IndexError: # possible segmentation fault or other error
    info_flow = "ERROR"
  return (time, info_flow, timeout)

def run_exp(exp_filename):
  logfile.write("Now running experiment " + exp_filename + "\n")
  # if options.cnf isn't set, then run CBMC first to generate CNFs then do this
  if exp_filename not in results_dict:
    results_dict[exp_filename] = {}
    results_dict[exp_filename][SCALMC] = []
    results_dict[exp_filename][SHARPCDCL] = []
  if options["cnf"]:
    logfile.write("    Running approxmc-p.py... ")
    # run scalmc
    (time, info_flow, timeout) = run_scalmc(exp_filename)
    scalmc_result = Result(time, info_flow, exp_filename, timeout)
    logfile.write("done: " + str(scalmc_result) + "\n")
    results_dict[exp_filename][SCALMC].append(scalmc_result)
    
    # run their model counter
    logfile.write("    Running sharpCDCL... ")
    (time, info_flow, timeout) = run_sharpCDCL(exp_filename)
    sharpcdcl_result = Result(time, info_flow, exp_filename, timeout)
    logfile.write("done: " + str(sharpcdcl_result) + "\n")
    results_dict[exp_filename][SHARPCDCL].append(sharpcdcl_result)
    
    # if all the observations are empty, then this experiment failed for some reason, so remove it? or put a special value here
    empty = True
    for tool in results_dict[exp_filename]:
      if len(results_dict[exp_filename][tool]) > 0:
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
  
  for exp in files:
    for i in xrange(options["runs"]):
      run_exp(exp)
  
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
    for tool in results_dict[exp]:
      print("    Results for " + tool + ":")
      for result in results_dict[exp][tool]:
        print("        " + str(result))
if __name__ == "__main__":
  main(sys.argv)
