#!/usr/bin/python
import tempfile, shutil

def merge_lines(filename, outfilename):
#def merge_lines(filename, strip_comments=False):
  temp_fn = None
  new_filename = None
  with open(filename, 'r') as cnf, tempfile.NamedTemporaryFile(delete=False) as cnf_new:
    new_filename = cnf_new.name
    
    problem_line = cnf.readline()
    if not (outfilename is None):
      print >> cnf_new, problem_line.rstrip()
    else:
      print problem_line.rstrip()
    problem = [tok for tok in problem_line.strip().split() if tok.strip() != ""]
    assert(problem[0] == "p")
    assert(problem[1] == "cnf")
    num_vars = int(problem[2])
 
    change_map = dict()
    change_map[0] = 0 # to avoid having to deal with the 0 entries (end of clause) as special cases

    clause = []
    for line in cnf:
      # for actual clause lines
      if line[0] != "c":
        toks = [e.strip() for e in line.strip().split()]
        # now read tokens until encountering 0
        try:
          clause += toks[:toks.index("0")]
          # print them, reset clause (to whatever was on the line after the 0) and move on to next iter
          print_string = (" ".join(clause) + " 0").strip()
          # don't print an empty clause (i.e. a lone 0 - clean up that case if present in CNF file)
          if print_string != "0":
            if not (outfilename is None):
              print >> cnf_new, print_string
            else:
              print print_string
          clause = toks[toks.index("0")+1:]
        except ValueError:
          # 0 wasn't found on that line, so add them to current clause and continue
          clause += toks
      # don't modify the comments, print them as-is
      #elif not strip_comments:
      else:
        if not (outfilename is None):
          print >> cnf_new, line,
        else:
          print line,
  if not (outfilename is None):
    shutil.move(new_filename, outfilename)

# all cnftools modules use a parser already
def get_argparser():
  import argparse

  parser = argparse.ArgumentParser(description='Place each clause on a single line in CNF file')
  parser.add_argument("cnf", metavar='cnf_file', help='DIMACS CNF source file')
  parser.add_argument("-out", "-o", "-outfile", "--out", "--o", "--outfile", metavar="outfile", help="Optional output file; if omitted prints to stdout", dest='outfile', required=False)
  #parser.add_argument("-sc", "-strip", "--strip-comments", help='Flag to strip comments from file when present', dest="strip_comments", action="store_true")
  return parser

def get_mode_names():
  return ("merge_lines", ["mergelines"])

def execute_module(args):
  cnf_fn = args.cnf
  out_fn = args.outfile
  #strip_comments = args.strip_comments
  #merge_lines(cnf_fn, strip_comments)
  merge_lines(cnf_fn, out_fn)

if __name__ == "__main__":
  execute_module(get_argparser().parse_args())
