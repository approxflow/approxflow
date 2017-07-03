#!/usr/bin/python
import tempfile, shutil

def sub_literals(cnf, cnf_new, change_map):
  for line in cnf:
    is_comment = (line[0] == 'c')
    possible_lits = [l.strip() for l in line.split()]
    #possible_lits = [l.strip() for l in line.split(" ") if l.strip() != ""]
    lits = []
    for lit in possible_lits:
      try:
        old_lit = int(lit)
        try:
          if old_lit < 0:
            new_lit = -1*change_map[abs(old_lit)]
          else:
            new_lit = change_map[abs(old_lit)]
        except KeyError:
          new_lit = old_lit
        lits.append(str(new_lit))
        #if str(old_lit) != str(new_lit):
          #print "{" + str(old_lit) + " -> " + str(new_lit) + "} ",
      except ValueError:
        if is_comment:
          lits.append(lit)
    print >> cnf_new, " ".join(lits)
    #print


def rename_literals(filename, from_list, to_list):
  #print from_list, to_list
  if len(to_list) < len(from_list):
    print "Error: from list length doesn't match to list length, not performing renaming"
    return
  from_list_without_dups_sorted = list(set([e for e in from_list]))
  from_list_without_dups_sorted.sort()
  from_list_sorted = [e for e in from_list]
  from_list_sorted.sort()
  if from_list_without_dups_sorted != from_list_sorted:
    print "Error: from_list -> to_list must be a function (each from_list entry must be unique), not performing renaming"
    return
  temp_fn = None
  new_filename = None
  with open(filename, 'r') as cnf, tempfile.NamedTemporaryFile(delete=False) as cnf_new:
    new_filename = cnf_new.name
    
    problem_line = cnf.readline()
    print >> cnf_new, problem_line.rstrip()
    problem = [tok for tok in problem_line.strip().split()]
    #problem = [tok for tok in problem_line.strip().split(" ") if tok.strip() != ""]
    assert(problem[0] == "p")
    assert(problem[1] == "cnf")
    num_vars = int(problem[2])
 
    change_map = dict()
    change_map[0] = 0 # to avoid having to deal with the 0 entries (end of clause) as special cases

    for i in range(len(from_list)):
      change_map[from_list[i]] = to_list[i]
    all_vars = range(1, num_vars+1)
    avail_to_list = list(set(all_vars) - set(to_list))
    avail_to_index = 0
    for lit in list(set(all_vars) - set(from_list)):
      try:
        change_map[lit]
        assert(1 == 2) # should not get here
      except KeyError:
        change_map[lit] = avail_to_list[avail_to_index]
        avail_to_index += 1
    sub_literals(cnf, cnf_new, change_map)
  shutil.move(new_filename, filename)

# all cnftools modules use a parser already
def get_argparser():
  import argparse
  def lit_parser(string):
    import re
    lit_invalid = False
    try:
      as_int = int(string)
      assert(as_int > 0)
      return [as_int] # return as list for convenience because range literals will return lists of lits too
    except ValueError:
      # try to interpret as a python range
      from_and_to_pattern = "\s*[1-9][0-9]*:[1-9][0-9]*:?((-[1-9])|([1-9])[0-9]*)*\s*" # handles a:b:c, a:b, a:b:
      no_from_pattern = "\s*:[1-9][0-9]*:?((-[1-9])|([1-9])[0-9]*)*\s*" # handles :b:c, :b, :b:
      full_pattern = "(" + from_and_to_pattern + ")|(" + no_from_pattern + ")" # two regex groups
      r = re.compile(full_pattern)
      if r.match(string):
        parts = string.split(":")
        try:
          start = int(parts[0])
        except ValueError:
          start = 1
        try:
          stop = int(parts[1])
        except IndexError:
          lit_invalid = True
        try:
          step = int(parts[2])
        except IndexError:
          if start <= stop:
            step = 1
          else:
            step = -1
        # for convenience, fix the sign of the step
        if (start <= stop):
          return range(start, stop+1, abs(step))
        else:
          return range(start, stop-1, -1*abs(step))
      lit_invalid = True

    if lit_invalid:
      raise argparse.ArgumentTypeError("%r is not a valid literal identifier or range of the form [start]:end[:][step]" %string)

  parser = argparse.ArgumentParser(description='Rename variables in a CNF file')
  parser.add_argument("-cnf", "-fn", "--file", "--cnf", metavar='cnf_file', help='DIMACS CNF source file', dest="cnf_fn", required=True)
  parser.add_argument("-f", "-from", "--from", metavar='from_list', type=lit_parser, nargs='+', help='list of source integers to convert, where multiple entries forming a range can be written as [start]:stop[:][step], e.g. 1:5:2 is the same as writing 1 3 5', dest="from_lits", required=True)
  parser.add_argument("-t", "-to", "--to", metavar='to_list', type=lit_parser, nargs='+', help='list of destination integers to which to convert, where multiple entries forming a range can be written as [start]:stop[:][step], e.g. 1:5:2 is the same as writing 1 3 5', dest="to_lits")
  return parser

# optional special function to return a fixed name (not dependent on filename) and/or aliases,
# this must return a tuple or list that when flattened, where the first element is a real 'name'
# of the module, and the rest are aliases (represents a name to aliases mapping)
def get_mode_names():
  from itertools import product
  first = ["rename", "renumber", "reorder"]
  second = ["literals", "literal", "lits", "lit", "l"]
  separators = ["_", "-"]
  prod = list(product(first, second))
  alias_list = []
  main_name = "rename"
  for sep in separators:
    for s in [sep.join(e) for e in prod]:
      if s != main_name:
        alias_list.append(s)
  alias_list.extend(list(set(first + [main_name]) - set([main_name])))
  return (main_name, alias_list)

# mandatory special function to actually perform the functionality of the module, given
# argparse-parsed args
def execute_module(args):
  def flatten(nested):
    for i in nested:
      if type(i) in [list, tuple]:
        for j in flatten(i):
          yield j
      else:
        yield i

  if args.to_lits == None:
    to_lits = None
  else:
    to_lits = list(flatten(args.to_lits))
  from_lits = list(flatten(args.from_lits))
  cnf_fn = args.cnf_fn

  if not to_lits or (len(to_lits) < len(from_lits)):
    to_lits = range(1, len(from_lits)+1)

  if not from_lits or (len(from_lits) < len(to_lits)):
    raise IndexError("from_list is smaller than to_list")

  def get_seq(l):
    if len(l) == 0:
      return False
    elif len(l) == 1:
      return (l[0], l[0], 1)
    elif len(l) == 2:
      return (l[0], l[1], l[1]-l[0])
    #if len(l) < 3:
    #  return False
    else:
      diff = l[1] - l[0]
      for i in range(1, len(l)-1):
        if (l[i+1] - l[i] != diff):
          return False
    return (l[0], l[len(l)-1], diff)

  rename_literals(cnf_fn, from_lits, to_lits)
  seq = get_seq(to_lits)
  if seq:
    s = "range " + str(seq[0]) + ":" + str(seq[1])
    if (abs(seq[2]) != 1):
      s = s + ":" + str(seq[2])
    print s
    #s = "range " + str(seq[0]) + " " + str(seq[1])
    #if abs(seq[2]) != 1:
    #  s = s + " " + str(seq[2])
    #print s
    #print "range", min(to_lits), max(to_lits)
  else:
    print "list", " ".join([str(lit) for lit in to_lits]) 

# if run as standalone script
if __name__ == "__main__":
  execute_module(get_argparser().parse_args())
