#!/usr/bin/python
import os

if __name__ == "__main__":
  cnf_fns = [e for e in os.listdir(".") if e[-4:] == ".cnf"]
  for cnf_fn in cnf_fns:
    with open(cnf_fn, 'r') as f:
      file_lines = f.read().split("\n")
      new_file_lines = []
      allsat_vars = None
      
      for line in file_lines:
        if line[:2] == "cr":
          new_file_lines.append(line.strip() + " 0")
          allsat_vars = line.split()[1:]
          [int(v) for v in allsat_vars] # error check
          
          i = 0
          while i < len(allsat_vars):
            tokens = allsat_vars[i:i+10]
            new_file_lines.append("c ind " + " ".join([str(e) for e in tokens]) + " 0")
            i += 10
        else:
          new_file_lines.append(line)
    assert(len(new_file_lines) >= len(file_lines))
    with open(cnf_fn, "w+") as f:
      f.write("\n".join(new_file_lines))
    with open(cnf_fn + ".scope", "w+") as f:
      f.write("\n".join(allsat_vars))

