#!/usr/bin/python
import re, subprocess

def get_allsat_vars(cnffile):
  # search for __return_value!i@j#k, and assume only k changes (should be true if there's only a single function converted to single return point named __return_value
  (i, j, k) = (None, None, -1)
  re_to_match = re.compile("global_consumption#[0-9]+")
  max_lits = None
  for line in cnffile:
    if line.startswith("c"):
      match = re_to_match.search(line)
      if match:
        m = match.group(0).split("global_consumption!")[0]
        new_k = int(m.split("#")[1])
        if (new_k > k):
          k = new_k
          max_lits = [int(var) for var in line.split()[2:] if var.lower() not in ["true", "false"]]
          # apparently, CBMC can report duplicate entries here?? Or is it a bug somewhere in my toolchain? [but where, I'm not using any cnftools etc before this point...] -- so, just make it unique
          if max_lits:
            return list(set(max_lits)) # order shouldn't matter so just turn it into a set then into a list again 

if __name__ == "__main__":
  with open("GuessPresenceAll.c.param", 'r') as f:
    s = f.read()
  #for N in xrange(3,17):
  # for N in 36, 49, 64, ... up to 17^2
  for N in [x*y for (x,y) in zip(xrange(3, 9), xrange(3,9))]:
    for case in [1, 2]:
      cfilename = "GuessPresenceAll.N" + str(N) + ".case" + str(case) + ".c"
      with open(cfilename, "w+") as f:
        f.write("#define CONST_N " + str(N) + "\n#define CONST_CASE " + str(case) + "\n\n" + s)
  
      p = subprocess.Popen(["cbmc"] + [cfilename, "--32", "--dimacs", "--outfile", cfilename + ".cnf"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      out, err = p.communicate()

      allsat_vars = None
      with open(cfilename + ".cnf", "r") as cnffile:
        cnfstr = cnffile.read()
      with open(cfilename + ".cnf", "r") as cnffile:
        allsat_vars = get_allsat_vars(cnffile)
     
      i = 0
      commentstr = ""
      with open(cfilename + ".cnf", "w+") as cnffile:
        while i < len(allsat_vars):
          tokens = allsat_vars[i:i+10]
          commentstr += "c ind " + " ".join([str(e) for e in tokens]) + " 0\n" # this won't work for > 10 vars
          i += 10
        commentstr += "cr " + " ".join([str(e) for e in allsat_vars]) + " 0\n"
        cnffile.write(cnfstr + "\n" + commentstr)
      with open(cfilename + ".cnf.scope", "w+") as scopefile:
        scopefile.write("\n".join([str(e) for e in allsat_vars]))

