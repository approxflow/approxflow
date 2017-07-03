#!/usr/bin/python

if __name__ == "__main__":
  import argparse
  from sys import argv
  import os
  import inspect

  def flatten(nested):
    for i in nested:
      if type(i) in [list, tuple]:
        for j in flatten(i):
          yield j
      else:
        yield i

  def strip(s):
    return s.strip().replace(" ", "").replace("\t", "").replace("\r", "").replace("\r", "")

  script_filename = os.path.realpath(__file__) # follow symlink
  base_module_name = os.path.splitext(os.path.basename(script_filename))[0]

  def get_module_name(f):
    return os.path.splitext(os.path.basename(f))[0]

  def get_inferred_mode_name(f):
    return get_module_name(f)[len(base_module_name + "_"):]

  def is_valid_module(f):
    if not f.startswith(base_module_name + "_"):
      return False

    # all modules must implement a 0-arity function returning an argparser for the standalone
    # module, with the function called get_argparser
    try:
      exec("from " + get_module_name(f) + " import get_argparser", globals(), locals())
      if len(inspect.getargspec(get_argparser).args) != 0:
        return False
    except ImportError, TypeError: # ImportError from the exec import statement, TypeError if get_arg_parser is not a function but a different Python object
      return False

    # all modules must implement their main functionality in a function called execute_module of
    # arity 1, where the sole argument is args, an argparse-parsed bunch of arguments
    try:
      exec("from " + get_module_name(f) + " import execute_module", globals(), locals())
      if len(inspect.getargspec(execute_module).args) != 1:
        return False
    except ImportError, TypeError: # ImportError from the exec import statement, TypeError if get_arg_parser is not a function but a different Python object
      return False
    
    # if we manage to get here without catching an error, it seems to have been implemented as a proper module
    return True

  def get_mode_names_from_module(f):
    if not is_valid_module(f):
      return () # or should it be None in this case?
    try:
      exec("from " + get_module_name(f) + " import get_mode_names", globals(), locals())
      if len(inspect.getargspec(get_mode_names).args) != 0:
        return ()
    except ImportError, TypeError:
      return ()
    names = get_mode_names()
    if type(names) == str:
      return (strip(names), []) # maps realname to nothing
    elif type(names) in [list, tuple]:
      names = list(flatten(names))
      for e in names:
        if type(e) != str:
          return []  
      return (strip(names[0]), [strip(a) for a in names[1:]])
    else: # if the wrong type was returned
      return []

  # valid modules have the same name as the base module, followed by and underscore and then the module name,
  # and they must implement the function get_argparser() of arity 0
  valid_modes = dict()
  reverse_valid_modes = dict()
  import_name_mapping = dict()
  completed_inferred_names = []

  for f in os.listdir(os.path.dirname(script_filename)):
    if is_valid_module(f):
      inferred_mode_name = get_inferred_mode_name(f) # implicit is module name inferred from filename
      if inferred_mode_name in completed_inferred_names: # don't double count if there's a .py and a .pyc file with same base name
        continue

      real_mode_name = get_mode_names_from_module(f)[:1]
      if len(real_mode_name) == 0:
        real_mode_name = strip(inferred_mode_name)
      else:
        real_mode_name = real_mode_name[0]

      mode_aliases = get_mode_names_from_module(f)[1:]
      if len(mode_aliases) == 0:
        mode_aliases = []
      else:
        mode_aliases = mode_aliases[0]

      if inferred_mode_name != real_mode_name:
        mode_aliases = [inferred_mode_name] + mode_aliases
      import_name_mapping[real_mode_name] = inferred_mode_name
      valid_modes[real_mode_name] = mode_aliases
      for name in mode_aliases:
        reverse_valid_modes[name] = real_mode_name
      reverse_valid_modes[real_mode_name] = real_mode_name # identity mapping for convenience      
      completed_inferred_names.append(inferred_mode_name)


  bad_first_arg = (len(argv) < 2)
  if not bad_first_arg:
    bad_first_arg = (argv[1] not in valid_modes and argv[1] not in reverse_valid_modes)

  if bad_first_arg:
    print("Usage: " + os.path.basename(argv[0]) + " <mode> [<options> ...]")
    print("  * where <mode> is one of (" + ", ".join(sorted(valid_modes.keys())) + ")")
    print("  * and <options> are specific to the mode; run " + os.path.basename(argv[0]) + " <mode> --help to get help for a specific mode")
    exit(1)

  mode = reverse_valid_modes[argv[1]]
  # TODO what if multiple modules? and how would duplicate args be handled?
  module_name = base_module_name + "_" + import_name_mapping[mode]
  exec("import " + module_name, globals(), locals())
  exec("parser = " + module_name + ".get_argparser()", globals(), locals())
  args_to_mode = argv[2:]
  parser = locals()["parser"]
  # dynamically add a list of aliases as an option
  #parser.add_argument("-aliases", "-alias", "--aliases", "--alias", help="List aliases for this subcommand", action="store_true", dest="aliases")
  args = parser.parse_args(args_to_mode)
  #if args.aliases:
  #  print args
  
  exec("from " + module_name + " import execute_module", globals(), locals())

  # finally, execute our cnftools module
  execute_module(args)
