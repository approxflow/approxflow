#!/usr/bin/python
import sys, re

allsat_vars = None
def get_allsat_vars(filename, name):
  re_to_match = re.compile(name + "::![0-9]+@[0-9]+#[0-9]+")
  # search for __return_value!i@j#k, and assume only k changes (should be true if there's only a single function converted to single return point named __return_value
  with open(filename, "r") as cnffile:
    (i, j, k) = (None, None, -1)
    max_lits = None
    for line in cnffile:
      if line.startswith("c"):
        match = re_to_match.search(line)
        if match:
          assert(len(match.groups()) == 1)
          m = match.group(0).split("__return_value!")[1]
          assert(i == None or i == int(m.split("@")[0]))
          assert(j == None or j == int(m.split("#")[0].split("@")[1]))
          new_k = int(m.split("#")[1])
          if (new_k > k):
            k = new_k
            max_lits = [int(var) for var in line.split()[2:] if var.lower() not in ["true", "false"]]
    # apparently, CBMC can report duplicate entries here?? Or is it a bug somewhere in my toolchain? [but where, I'm not using any cnftools etc before this point...] -- so, just make it unique
    if max_lits:
      return list(set(max_lits)) # order shouldn't matter so just turn it into a set then into a list again

print(get_allsat_vars(sys.argv[1], sys.argv[2]))