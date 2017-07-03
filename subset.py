#!/usr/bin/python

# requires assert(var == 0) to be on a single line, with var first, and == 0
# (and == 0 coming after it)
if __name__ == "__main__":
  import sys
  sys.path.append("cnftools")
  from cnftools_rename import sub_literals, rename_literals
  import argparse
  import re

  parser = argparse.ArgumentParser(description='Rename variables in a CNF file')
  parser.add_argument("-c", "--cfile", metavar='cfile', help="name of C source code file", dest="c_fn", required=True)
  parser.add_argument("-cnf", "--cnffile", metavar='cnffile', help="DIMACS CNF source file", dest="cnf_fn", required=True)
  parser.add_argument("-f", "--fun", metavar='funcname', help="Name of entry point function in C source file", dest="function_name", required=True)
  args = parser.parse_args()

  c_fn = args.c_fn
  cnf_fn = args.cnf_fn
  function_name = args.function_name
  # identify assert variable
  from_lits = []
  to_lits = []
  with open(c_fn, 'r') as cfile, open(cnf_fn, 'r') as cnffile:
    literals = []
    regex_assertion = re.compile("assert\s*\(\s*[a-zA-Z_]+[a-zA-Z0-9_]*\s*==\s*\.*0\s*\)")
    for c_line in cfile:
      if regex_assertion.search(c_line):
        varname = re.split("assert\s*\(", c_line.strip().split("==")[0].strip())[1]
        cnf_pre_count_id = "c c::" + function_name + "::[0-9]+::" + varname + "![0-9]+@[0-9]+#"
        cnf_pre_count_id2 = "c c::" + function_name + "::[0-9]+::" + varname + "(\$[a-z0-9A-Z_])*![0-9]+@[0-9]+#"
        cnf_id = cnf_pre_count_id + "[0-9]+"
        regex_cnf = re.compile(cnf_pre_count_id2 + "[0-9]+")
        max_id = -1
        for cnf_line in cnffile:
          if regex_cnf.search(cnf_line):
            split_numbers = re.split(cnf_pre_count_id, cnf_line.strip())[1].split(" ")
            cur_id = int(split_numbers[0])
            if cur_id > max_id:
              max_id = cur_id
              literals = split_numbers[1:]
            
        unknown_lits = []
        for lit in literals:
          try:
            if int(lit) not in [int(l) for l in unknown_lits]:
              unknown_lits.append(str(int(lit)))
          except ValueError:
            pass
        #print " ".join(unknown_lits)
        from_lits = [int(lit) for lit in unknown_lits]
        to_lits = range(1, len(from_lits)+1)
        break # only do the first one

  def is_seq(l):
    l.sort()
    if len(l) < 2:
      return True
    else:
      for i in range(len(l)-1):
        if (l[i+1] - l[i] != 1):
          return False
    return True

  rename_literals(cnf_fn, from_lits, to_lits)
  if len(to_lits) == 0:
    print "simplified"
  elif is_seq(to_lits):
    print "range", min(to_lits), max(to_lits)
  else:
    print "list", " ".join(to_lits)
