#!/usr/bin/python
import tempfile, subprocess, os


def stat(filename):
  external_tool = os.path.join(os.path.dirname(os.path.realpath(__file__)), "vegard-cnf-utils", "cnf-stat")
  tool_name = os.path.join(os.path.basename(os.path.split(external_tool)[0]), os.path.basename(external_tool))
  args = filename
  new_filename = None
  try:
    p = subprocess.Popen([external_tool, filename])
    p.wait()
    if p.returncode != 0:
      #print "Error: Nonzero return code (" + str(p.returncode) + ") from " + tool_name + ", exiting"
      return
  except OSError:
    print "Error: external tool " + tool_name + " not found, not performing stat"

# all cnftools modules use a parser already
def get_argparser():
  import argparse

  parser = argparse.ArgumentParser(description='Print some simple statistics about the CNF input (courtesy of Vegard Nossum, https://github.com/vegard/cnf-utils)')
  parser.add_argument("cnf", metavar='cnf_file', help='DIMACS CNF source file')
  #parser.add_argument("-sc", "-strip", "--strip-comments", help='Flag to strip comments from file when present', dest="strip_comments", action="store_true")
  return parser

def get_mode_names():
  from itertools import product
  first = ["cnf"]
  second = ["stat", "stats", "statistics", "statistic"]
  separators = ["_", "-"]
  prod = list(product(first, second))
  alias_list = []
  main_name = "stat"
  for sep in separators:
    for s in [sep.join(e) for e in prod]:
      if s != main_name:
        alias_list.append(s)
  alias_list.extend(list(set(second + [main_name]) - set([main_name])))
  return (main_name, alias_list)

def execute_module(args):
  cnf_fn = args.cnf
  #strip_comments = args.strip_comments
  #merge_lines(cnf_fn, strip_comments)
  stat(cnf_fn)

if __name__ == "__main__":
  execute_module(get_argparser().parse_args())
