#!/usr/bin/python
import tempfile, shutil, subprocess, os


def pack(filename):
  external_tool = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vegard-cnf-utils", "cnf-propagate")
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
      print "Error: external tool " + tool_name + " not found, not performing unit propagation"
      return
  shutil.move(new_filename, filename)

# all cnftools modules use a parser already
def get_argparser():
  import argparse
  parser = argparse.ArgumentParser(description='Perform unit propagation recursively on the CNF until no more can be done; no clauses (including tautologies) are removed (courtesy of Vegard Nossum, https://github.com/vegard/cnf-utils)')
  parser.add_argument("cnf", metavar='cnf_file', help='DIMACS CNF source file')
  return parser

def get_mode_names():
  from itertools import product
  first = ["unit"]
  second = ["propagate", "prop", "p", "propag", "propagation"]
  separators = ["_", "-"]
  prod = list(product(first, second))
  alias_list = []
  main_name = "propagate"
  for sep in separators:
    for s in [sep.join(e) for e in prod]:
      if s != main_name:
        alias_list.append(s)
  alias_list.append("propagation")
  return (main_name, alias_list)

def execute_module(args):
  cnf_fn = args.cnf
  pack(cnf_fn)

if __name__ == "__main__":
  execute_module(get_argparser().parse_args())
