import sys, subprocess, math

try:
  from scipy.misc import comb
except:
  # factorial
  def fact(n, acc=1):
    return acc if n <= 1 else fact(n-1, acc*n)
  # combinations of n, taken k at a time
  # TODO: horribly inefficient
  def comb(n, k):
    return fact(n) / (fact(k) * fact(n-k))

# implements optimization given by Kuldeep in the paper, though it's written wrong there
# (missing ceiling where it says nu(t, t/2, 0.4) -- should be nu(t, ceil(t/2), 0.4)
def compute_iter_count(delta):
  # starting value, this is the "unoptimized" iteration count
  basic_num_iterations = int(math.ceil(35 * math.log(3.0/delta, 2)))
  
  # compute smallest # of iterations t possible such that
  # sum from k=ceil(t/2) to k=t of (t choose k) * 0.4^k * (0.6)^(t-k)
  
  # TODO: likely a pretty inefficient implementation
  min_t = None
  for t in reversed(xrange(1, basic_num_iterations+1)):
    prob = 0
    for k in range(int(math.ceil(t/2.0)), t+1):
      prob += comb(t, k) * 0.4**k * 0.6**(t-k)
    if min_t is None or (t < min_t and prob <= delta):
      min_t = t
  
  return min_t

def run_scalmc(argv, epsilon=None, delta=None):
  for e in [epsilon, delta]:
    if e != None:
      try:
        efloat = float(e)
        if efloat <= 0 and efloat >= 1:
          raise ValueError("Parameter " + e + " must be greater than 0 and less than 1")
      except:
        raise ValueError("Parameter " + e + " must be a floating-point value greater than 0 and less than 1")

  def exit_param(param):
    print("Format: --" + param + "=" + param[0] + " where " + param[0] + " > 0 and " + param[0] + " < 1")
    exit(1)
  new_args = []
  opt_dict = {}
  #to_replace_dict = {} # pivotAC and t
  for arg in argv:
    if arg in ["--help", "-h"]:
      p = subprocess.Popen(["scalmc", "--help"], stdout=sys.stdout, stderr=sys.stderr)
      (out, err) = p.communicate()
      print("ApproxMC Driver Options:")
      print("  --epsilon                          epsilon value from paper (greater than 0\n                                     and less than 1) (tolerance value)")
      print("  --delta                            delta value from paper (greater than 0\n                                     and less than 1) (1-delta is confidence)")
      exit(1)
      
  for arg in argv:
    if arg[:2] == "--":
      split = arg[2:].split("=")
      opt = split[0]
      val = split[1]
      if len(split) < 2:
        print("Unknown option " + arg)
        exit(1)
      if opt in ["epsilon", "delta"]:
        if epsilon != None and opt == "epsilon":
          opt_dict[opt] = epsilon
          break
        elif delta != None and opt == "delta":
          opt_dict[opt] = delta
          break
        else:
          opt_dict[opt] = None
          try:
            opt_dict[opt] = float(val)
            if opt_dict[opt] <= 0 or opt_dict[opt] >= 1:
              exit_param(opt)
          except:
            exit_param(opt)
    #import IPython; IPython.embed()
    if ((arg.startswith("--pivotAC=") and "epsilon" not in opt_dict) or (arg.startswith("--tApproxMC=") and "delta" not in opt_dict)) or ((not arg.startswith("--epsilon=")) and (not arg.startswith("--delta="))):
    
    
    #if (arg.startswith("--pivotAC=") and "epsilon" not in opt_dict) or (arg.startswith("--tApproxMC=") and "delta" not in opt_dict) or not arg.startswith("--epsilon=") or not arg.startswith("--delta="):
      new_args.append(arg)
  
  # if it's an actual call and not a script
  if "epsilon" not in opt_dict and epsilon != None:
    opt_dict["epsilon"] = epsilon
  if "delta" not in opt_dict and delta != None:
    opt_dict["delta"] = delta
  
  final_arg = new_args[-1]
  new_args = new_args[:-1]
  if "epsilon" in opt_dict:
    #pivot = 2 * math.floor(3*(math.e**0.5)*(1+(1.0/opt_dict["epsilon"]))**2)
    pivot = 2 * math.ceil(3*(math.e**0.5)*(1+(1.0/opt_dict["epsilon"]))**2)
    assert(int(round(pivot)) == int(pivot))
    new_args.append("--pivotAC=" + str(int(pivot)))
  if "delta" in opt_dict:
    iterations = compute_iter_count(opt_dict["delta"])
    assert(int(round(iterations)) == int(iterations))
    new_args.append("--tApproxMC=" + str(int(iterations)))

  new_args.append(final_arg)

  # if it's an actual call and not a script
  if epsilon != None or delta != None:
    p = subprocess.Popen(["scalmc"] + new_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  else:
    p = subprocess.Popen(["scalmc"] + new_args, stdout=sys.stdout, stderr=sys.stderr)
  (out, err) = p.communicate()
  return (out, err)

if __name__ == "__main__":
  run_scalmc(sys.argv[1:])
