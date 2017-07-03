#!/usr/bin/python
import tempfile, shutil, subprocess, os


def shuffle(filename):
  external_tool = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vegard-cnf-utils", "cnf-shuffle-variables")
  args = filename
  new_filename = None
  with tempfile.NamedTemporaryFile(delete=False) as cnf_new:
    new_filename = cnf_new.name
    try:
      p = subprocess.Popen([external_tool, filename], stdout=cnf_new)
      p.wait()
      if p.returncode != 0:
        #print "Error: Nonzero return code (" + str(p.returncode) + ") from " + tool_name + ", exiting"
        return
    except OSError:
      tool_name = os.path.join(os.path.basename(os.path.split(external_tool)[0]), os.path.basename(external_tool))
      print "Error: external tool " + tool_name + " not found, not performing variable shuffling"
      return
  shutil.move(new_filename, filename)

# all cnftools modules use a parser already
def get_argparser():
  import argparse

  parser = argparse.ArgumentParser(description='Rename the variables randomly using a one-to-one mapping. The resulting CNF output is equisatisfiable with the CNF input (courtesy of Vegard Nossum, https://github.com/vegard/cnf-utils)')
  parser.add_argument("cnf", metavar='cnf_file', help='DIMACS CNF source file')
  return parser

def get_mode_names():
  from itertools import product
  first = ["shuffle", "shuf", "shuff"]
  second = ["variables", "vars", "variable", "var", "v"]
  separators = ["_", "-"]
  prod = list(product(first, second))
  alias_list = []
  main_name = "shuffle_variables"
  for sep in separators:
    for s in [sep.join(e) for e in prod]:
      if s != main_name:
        alias_list.append(s)
  return (main_name, alias_list)

def execute_module(args):
  cnf_fn = args.cnf
  shuffle(cnf_fn)

if __name__ == "__main__":
  execute_module(get_argparser().parse_args())
