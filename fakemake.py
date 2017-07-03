#!/usr/bin/python
import sys, os, re, collections

use_py33_subprocess = True
try:
  sys.path.append("util/subprocess32-py3.3-backport")
except ImportError:
  use_py33_subprocess = False
use_py33_subprocess = False # TODO remove this once fixing _posixsubprocess import issues
if use_py33_subprocess:
  import subprocess32 as subprocess
else:
  import subprocess

DEP_FILENAME = "DEPENDENCY_OUTPUT.TXT"
ORIGINAL_WD = None


def run_make():
  try:
    with open(os.path.join(ORIGINAL_WD, DEP_FILENAME), "w+") as outfile:
      p = subprocess.Popen(["./configure"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print("Running configure script...")
      p.communicate()
      print("Done configuring.")
      p = subprocess.Popen(["make", "-k", "-d"], stdin=subprocess.PIPE, stdout=outfile, stderr=subprocess.PIPE)
      print("Running make...")
      p.communicate()
      print("Done making.")
  finally:
    try:
      # p = subprocess.Popen(["make", "clean"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      # print("Running clean...")
      # p.communicate()
      # print("Done cleaning.")
      pass
    except: pass
  

def get_cur_dir(line):
  s = ""
  try:
    return get_basedir(strip_maketarget(line.split("Considering target file")[1]))
    #return find_root_dir(get_basedir(strip_maketarget(line.split("Considering target file")[1])))
  except:
    return None

def get_basedir(path):
  path = os.path.split(path)[0]
  try:
    if os.path.split(path)[1] == ".deps":
      path = os.path.split(path)[0]
  except: pass
  return path

def strip_maketarget(string):
  string = string.strip() # whitespace
  assert(string[-1] == ".") # get rid of dot it adds
  string = string[:-1]
  assert(string[-1] == "'" and string[0] == "'")
  string = string.strip("'") # get rid of '
  return string

def print_deps(d):
  for e in d:
    print(e)

#look for special file THIS_IS_BASE_DIR
def find_root_dir(filename):
  cur = get_basedir(filename)
  while cur != "" and cur != os.path.sep and not os.path.exists(cur + os.path.sep + "THIS_IS_BASE_DIR"):
    cur = get_basedir(cur)
  if cur == os.path.sep:
    cur = ""
  if cur == "":
    cur = get_basedir(filename) # return the original, can't go all the way back to root
  return cur

def get_deps(filename):
  global ORIGINAL_WD
  print("Getting build dependencies of " + filename)
  root_dir = find_root_dir(filename)
  ORIGINAL_WD = os.getcwd()
  os.chdir(root_dir)
  run_make()
  os.chdir(ORIGINAL_WD)
  #try: os.remove(DEP_FILENAME)
  #except: pass
  # First, find the root directory


  base_dir = ""
  if len(os.path.split(DEP_FILENAME)[0]) == "":
    base_dir = os.path.split(DEP_FILENAME)[0]
  cur_dir = ""
  #i = 0
  dirs = collections.OrderedDict() # use it as an ordered set
  with open(DEP_FILENAME, "r") as f:
    for line in f:
      if get_cur_dir(line) != None:
        cur_dir = base_dir + get_cur_dir(line)
        dirs[cur_dir] = None
      #i += 1
      #if i >= 1000000:
      #  break
  # remove internal compilation stuff, bit hacky
  to_remove = [d for d in dirs if os.path.sep + "bits" + os.path.sep in d or os.path.sep + "bits" == d[-5:]]
  for e in to_remove:
    del dirs[e]
  # print("~~~~~~~~~~ ROOT DIR: " + root_dir + " ~~~~~~~~~~\n")
  # dirs[root_dir] = None # append root directory too
  #dirs[""] = None
  # for e in dirs:
    # print(e)
  # exit(1)
  return dirs

def main(filename):
  get_deps(filename)

def run_as_script(filename):
  print(" ".join([e for e in get_deps(filename)]))

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("usage: " + argv[0] + " filename")
    exit(1)
  
  run_as_script(sys.argv[1])
