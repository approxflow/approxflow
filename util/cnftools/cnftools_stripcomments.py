#!/usr/bin/python
import tempfile, shutil

def strip_comments(filename):
  temp_fn = None
  new_filename = None
  with open(filename, 'r') as cnf, tempfile.NamedTemporaryFile(delete=False) as cnf_new:
    new_filename = cnf_new.name
    
    for line in cnf:
      stripped = line.lstrip()
      print_line = False
      if len(stripped) > 0:
        if stripped[0] != "c":
          print_line = True
      else:
        print_line = True
      if print_line:
        print >> cnf_new, line,

  shutil.move(new_filename, filename)

# all cnftools modules use a parser already
def get_argparser():
  import argparse

  parser = argparse.ArgumentParser(description='Strip comments from a DIMACS CNF file')
  parser.add_argument("cnf", metavar='cnf_file', help='DIMACS CNF source file')
  return parser

def get_mode_names():
  return ("strip_comments", ["comments"])

def execute_module(args):
  cnf_fn = args.cnf
  strip_comments(cnf_fn)

if __name__ == "__main__":
  execute_module(get_argparser().parse_args())
