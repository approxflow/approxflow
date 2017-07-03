#!/usr/bin/python
import tempfile, shutil

def logical_or(filename1, filename2):
  from cnftools_mergelines import merge_lines
  with open(filename1, 'r') as cnf1, open(filename2, 'r') as cnf2, tempfile.NamedTemporaryFile(delete=False) as cnf1_temp, tempfile.NamedTemporaryFile(delete=False) as cnf2_temp:
    cnf1_temp_fn = cnf1_temp.name
    cnf2_temp_fn = cnf2_temp.name
    merge_lines(filename1, cnf1_temp_fn)
    merge_lines(filename2, cnf2_temp_fn)

  #with open(filename1, 'r') as cnf1, open(filename2, 'r') as cnf2, tempfile.NamedTemporaryFile(delete=False) as cnf_new, tempfile.NamedTemporaryFile(delete=False) as cnf1_temp, tempfile.NamedTemporaryFile(delete=False) as cnf2_temp:
  with open(filename1, 'r') as cnf1, open(filename2, 'r') as cnf2, tempfile.NamedTemporaryFile(delete=False) as cnf_new:
    try:
      cnf1_temp = open(cnf1_temp_fn)
      cnf2_temp = open(cnf1_temp_fn)
      new_filename = cnf_new.name
      #cnf1_temp_fn = cnf1_temp.name
      #cnf2_temp_fn = cnf2_temp.name

      #merge_lines(filename1, cnf1_temp_fn)
      #merge_lines(filename2, cnf2_temp_fn)

      problems = [[tok for tok in cnf1.readline().strip().split() if tok.strip() != ""], \
                  [tok for tok in cnf2.readline().strip().split() if tok.strip() != ""]]
      num_vars = []
      for problem in problems:
        assert(problem[0] == "p")
        assert(problem[1] == "cnf")
        num_vars.append(int(problem[2]))
      # advance past the problem line
      cnf1_temp.readline()
      cnf2_temp.readline()
      clause2_reset_seek_pos = cnf2_temp.tell()
      for clause1 in cnf1_temp:
        toks1 = [tok.strip() for tok in clause1.split(" ") if tok != ""]
        if toks1[0] == "c":
          continue
        assert(toks1[-1] == "0")
        toks1 = toks1[:-1]
        for clause2 in cnf2_temp:
          toks2 = [tok.strip() for tok in clause2.split(" ") if tok != ""]
          if toks2[0] == "c":
            continue
          assert(toks2[-1] == "0")
          toks2 = toks2[:-1]
          if toks2 == toks1:
            continue
          toks1 += toks2
        cnf2_temp.seek(clause2_reset_seek_pos)
        print " ".join(toks1) + " 0"
    finally:
      cnf1_temp.close()
      cnf2_temp.close()

  #shutil.move(new_filename, filename)

# all cnftools modules use a parser already
def get_argparser():
  import argparse
  parser = argparse.ArgumentParser(description='Perform a logical OR of two CNF formulas into a new formula')
  parser.add_argument("cnf1", metavar='cnf_file1', help='First CNF file')
  parser.add_argument("cnf2", metavar='cnf_file2', help='Second CNF file')
  parser.add_argument("-out", "-o", "-outfile", "--out", "--o", "--outfile", metavar="out_file", help="filename where to dump CNF, prints to stdout if none given", dest="out_fn", required=False)
  return parser

# optional special function to return a fixed name (not dependent on filename) and/or aliases,
# this must return a tuple or list that when flattened, where the first element is a real 'name'
# of the module, and the rest are aliases (represents a name to aliases mapping)
def get_mode_names():
  from itertools import product
  first = ["logical"]
  second = ["or"]
  separators = ["_", "-"]
  prod = list(product(first, second))
  alias_list = []
  main_name = "logical_or"
  for sep in separators:
    for s in [sep.join(e) for e in prod]:
      if s != main_name:
        alias_list.append(s)
  alias_list.extend(list(set(first + [main_name]) - set([main_name])))
  alias_list.append("or")
  return (main_name, alias_list)

# mandatory special function to actually perform the functionality of the module, given
# argparse-parsed args
def execute_module(args):
  cnf_fn1 = args.cnf1
  cnf_fn2 = args.cnf2
  logical_or(cnf_fn1, cnf_fn2)

# if run as standalone script
if __name__ == "__main__":
  execute_module(get_argparser().parse_args())
