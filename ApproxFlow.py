#!/usr/bin/python
# Imports and path resolutions, etc.
###########################################

# for storing program options
class OptionsDict(dict):
  def __getattr__(self, key):
    try:
      return self[key]
    except KeyError as e:
      raise AttributeError(e)
  def __setattr__(self, key, value):
    self[key] = value
options = OptionsDict()

import re, math

import sys, os, shutil
sys.path.append("util")

options.use_py33_subprocess = True
try:
  sys.path.append("util/subprocess32-py3.3-backport")
except ImportError:
  options.use_py33_subprocess = False
options.use_py33_subprocess = False # TODO remove this once fixing _posixsubprocess import issues

import pycparser
from pycparser import c_parser, c_ast, parse_file, c_generator

if options.use_py33_subprocess:
  import subprocess32 as subprocess
else:
  import subprocess

import math, os, errno, ctypes
#import cinpy

sys.path.append("util")
sys.path.append("util/cnftools")
import cnftools_rename
# End of imports and path resolutions, etc.
###########################################

options.function = None
options.decide_all_functions = True
options.cnf_only = False
options.model_count_only = False

# for printing options
class VerbosityLevelsDict(dict):
  limit_dict = {"verbosity_max": False, "verbosity_min": False}
  def __getattr__(self, key):
    if key in self.limit_dict:
      return self.limit_dict[key]
    elif self.limit_dict["verbosity_max"] and not self.limit_dict["verbosity_min"]:
      return True
    elif self.limit_dict["verbosity_min"] and not self.limit_dict["verbosity_max"]:
      return False
    else:
      return self.key
  def __setattr__(self, key, value):
    if type(value) is not bool:
      raise ValueError("value " + str(value) + " to be added to verbosity dict is not of type bool")
    elif key == "verbosity_max":
      self.limit_dict["verbosity_max"] = value
    elif key == "verbosity_min":
      self.limit_dict["verbosity_min"] = value
    else:
      self[key] = value

# printing options

options.verbosity = VerbosityLevelsDict()
options.verbosity.verbosity_max = True # overrides all others, others may be false only if this is false
options.verbosity.verbosity_min = False # overrides all others, others may be false only if this is false
options.verbosity.print_cbmc_out = True
options.verbosity.print_cbmc_err = True
options.verbosity.print_modelcounter_out = True
options.verbosity.print_modelcounter_err = True

# Use build resolution if found
options.fakemake = True
try:
  import fakemake
except:
  options.fakemake = False
fakemake_includes = []

APPROX_MC = "c ind"
APPROX_MC_PY = "cr"
SHARPCDCL = "scope"
wrote_in_allsat_var_projection_scope = {APPROX_MC: set(), APPROX_MC_PY: set(), SHARPCDCL: set()}
# main program

class VarInfo:
  """
  Represents a C variable, storing the variable name, size, type, and other info
  """
  # maybe stores bitmasks up to size of size if known true/false (maybe not bits b/c "unknown" is a possible value"
  def __init__(self, name, size, type_name):
    self.name = name
    self.size = size
    self.type_name = type_name
  def __eq__(self, other):
    if type(self) is type(other):
      return self.__dict__ == other.__dict__
    return NotImplemented
  def __ne__(self, other):
    return not self.__eq__(other)
  def __key(self):
    return tuple([self.__dict__[field] for field in self.__dict__])
  def __hash__(self):
    return hash(self.__key())
  def __repr__(self):
    return self.__class__.__name__ + str("(" + ", ".join([str(key) + "=" + repr(self.__dict__[key]) for key in self.__dict__]) + ")")

ast = None
filename = None
tmpdir = "tmp"

# dictionary mapping function name to return value bit width size (upper bound on info flow) -- this is basically the output of this script
fn_ret_val_size_dict = {}
fn_params_dict = {}

# dictionary mapping function to our currently best-known information flow
# not that useful because we'll need to store learned clauses too
fn_info_flow_dict = {}

ret_val_assertion_text = "ret-val assertion"

# This will convert the program to single return point, and remove all assertions, inserting a single one on
# the return value instead
def insert_assertions(ast, new_filename):
  class InsertAssertionsGenerator(c_generator.CGenerator):
    is_func_body = False
    was_func_body = False
    is_func_body_type = False
    func_def = None
    func_return_type_str = None
    ret_value_var_name = "__return_value" # TODO possibly make it more complex based on function name or guarantee-unique
    # TODO this is broken and does not work
    def get_assertion_string_rec(self, stack_level, acc):
      # leaf
      #if type(self.func_return_type.type) in [c_ast.PtrDecl]:
      if type(self.func_def.decl.type) in [c_ast.PtrDecl]:
        acc += "__CPROVER_assert(0, \"" + ret_val_assertion_text + "\");\n"
        #acc += "__CPROVER_assert(" + self.ret_value_var_name + " == 0, \"" + ret_val_assertion_text + "\");\n"
        return acc
      #if type(self.func_return_type.type) is c_ast.TypeDecl:
      if type(self.func_def.decl.type) is c_ast.TypeDecl:
        acc += str(self.func_def.decl.type.type.names) + ", " + str(type(self.func_def))
        return acc
      #elif self.func_return_type in [c_ast.Compound]:
      #  acc += "compound"
      #  return acc
      #  #acc += ";\n".join(self.get_assertion_string_rec(c, stack_level+1, acc
      else:
        #raise TypeError("NYI, or return values can't have type " + str(self.func_return_type_str))
        n = self.func_def.decl.type
        n = self.func_def.decl.type
        print n, dir(n)
        raise TypeError("NYI, or return values can't have type " + str(type(self.func_def.decl.type)))
      #return str(type(self.func_return_type))

    def get_assertion_string(self):
      return "__CPROVER_assert(0, \"" + ret_val_assertion_text + "\");\n"
      #return "__CPROVER_assert(" + self.ret_value_var_name + " == 0, \"" + ret_val_assertion_text + "\")"

    # this is needed because the function body is a Compound
    def visit_Compound(self, n):
      s = self._make_indent() + '{\n'
      self.indent_level += 2
      # functions in C can only be defined at top level, so they always have an indent level of 2
      if self.is_func_body and self.func_return_type_str is not None and self.indent_level == 2:
        s += self._make_indent() + self.func_return_type_str + " " + self.ret_value_var_name + ";\n";
      self.is_func_body = False; # since it's recursive, don't want deeper nested blocks in the function to get this
      if n.block_items:
        s += ''.join(self._generate_stmt(stmt) for stmt in n.block_items)
      if self.was_func_body and self.func_return_type_str is not None and self.indent_level == 2:
        s += self._make_indent() + get_return_label_string() + ": " + self.get_assertion_string() + ";\n"
        #s += self._make_indent() + "__CPROVER_assert(" + self.ret_value_var_name + " == 0, \"ret-val assertion\");\n"
        s += self._make_indent() + "return " + self.ret_value_var_name + ";\n"
        self.was_func_body = False
      self.indent_level -= 2
      s += self._make_indent()
      s += '}\n'
      return s

    def _generate_type(self, n, modifiers=[]):
      typ = type(n)
      #~ print(n, modifiers)

      if typ == c_ast.TypeDecl:
        s = ''
        if n.quals:
          s += ' '.join(n.quals) + ' '
        s += self.visit(n.type)

        if self.is_func_body_type:
          nstr = ""
        else:
          nstr = n.declname if n.declname else ''
        # Resolve modifiers.
        # Wrap in parens to distinguish pointer to array and pointer to
        # function syntax.
        #
        for i, modifier in enumerate(modifiers):
          if isinstance(modifier, c_ast.ArrayDecl):
            if (i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl)):
              nstr = '(' + nstr + ')'
            nstr += '[' + self.visit(modifier.dim) + ']'
          elif isinstance(modifier, c_ast.FuncDecl):
            if (i != 0 and isinstance(modifiers[i - 1], c_ast.PtrDecl)):
              nstr = '(' + nstr + ')'
            nstr += '(' + self.visit(modifier.args) + ')'
          elif isinstance(modifier, c_ast.PtrDecl):
            if modifier.quals:
              nstr = '* %s %s' % (' '.join(modifier.quals), nstr)
            else:
              nstr = '*' + nstr
        if nstr:
          s += ' ' + nstr
        return s
      elif typ == c_ast.Decl:
        return self._generate_decl(n.type)
      elif typ == c_ast.Typename:
        return self._generate_type(n.type)
      elif typ == c_ast.IdentifierType:
        return ' '.join(n.names) + ' '
      elif typ in (c_ast.ArrayDecl, c_ast.PtrDecl, c_ast.FuncDecl):
        return self._generate_type(n.type, modifiers + [n])
      else:
        return self.visit(n)

    # change the body of the function definition
    def visit_FuncDef(self, n):
      decl = self.visit(n.decl)
      self.indent_level = 0
      ret_type = n.decl.type.type
      self.func_def = n
      if type(ret_type) in [c_ast.TypeDecl, c_ast.PtrDecl]:
        self.is_func_body_type = True
        c_type = self._generate_type(ret_type)
        if "*" in c_type or "void" not in c_type:
          self.func_return_type_str = c_type
        else:
          self.func_return_type_str = None
        self.is_func_body_type = False

      self.is_func_body = True
      self.was_func_body = True
      body = self.visit(n.body)
      self.is_func_body = False
      self.was_func_body = False
      #self.func_return_type_str = None
      self.is_func_body_type = False
      if n.param_decls:
        knrdecls = ';\n'.join(self.visit(p) for p in n.param_decls)
        return decl + '\n' + knrdecls + ';\n' + body + '\n'
      else:
        return decl + '\n' + body + '\n'

    def visit_Return(self, n):
      # change all returns to assignments; there will be a single return point, dealt with when generating the function body (at the end of the body)
      visit_rest_str = ""
      if n.expr:
        visit_rest_str = " " + self.visit(n.expr)

      if visit_rest_str:
        s = self.ret_value_var_name + " =" + visit_rest_str;
      else:
        s = "return"
      #return s + ";"
      return s + ";\n" + self._make_indent() + "goto " + get_return_label_string() + ";"

  insert_assertions_generator = InsertAssertionsGenerator()
  new_code_str = insert_assertions_generator.visit(ast)
  #print new_code_str
  with open(new_filename, 'w') as f:
    f.write(new_code_str)

# instead of single return point conversion, this generates a new function calling
# each function we need with nondet params, storing their ret vals there and then having
# a single assertion for *all* function ret vals as a disjunction of their return values
#
# Precondition: must be called only AFTER fn_params_dict is populated
def convert_to_compound_function(ast, filename):
  class CompoundFunctionGenerator(c_generator.CGenerator):
    def visit_FileAST(self, n):
      indent_level = 0
      s = super(self.__class__, self).visit_FileAST(n)
      # generate CBMC nondet calls for the param types we'll need
      type_to_nondet_name_dict = {}
      for fn in fn_params_dict:
        for var in fn_params_dict[fn]:
          try:
            type_to_nondet_name_dict[var.type_name]
          except KeyError:
            type_to_nondet_name_dict[var.type_name] = "nondet_" + var.type_name.replace(" ", "_").replace("*", "_ptr").strip()
      s += "\n"
      for type_name in type_to_nondet_name_dict:
        s += type_name + " " + type_to_nondet_name_dict[type_name] + "();\n"
      s += "\n"

      s += "\nvoid __retval_assertion_func(void)\n{\n"
      # call the functions with the nondet params
      ret_val_name = lambda name : "__ret_val_" + str(name)
      assert_cond_str = lambda var : var + " == 0"
      for fn in fn_params_dict:
        passed_params_str = ", ".join([type_to_nondet_name_dict[param.type_name] + "()" for param in fn_params_dict[fn]])
        s += " "*(indent_level+1) + ret_val_name(fn) + " = "  + str(fn) + "(" + passed_params_str  + ");\n"
      s += " "*(indent_level+1) + "__CBMC_assert("
      s += " || ".join(["(" + assert_cond_str(ret_val_name(k)) + ")" for k in fn_params_dict.keys()])
      #keys = fn_params_dict.keys()
      #s += " || ".join([assert_cond_str(ret_val_name(k)) for k in keys[:-1]]) + assert_cond_str(ret_val_name(keys[-1]))
      s += ", \"" + ret_val_assertion_text + "\");\n"
      s += "}\n"
      return s
  compound_function_assertion_generator = CompoundFunctionGenerator()
  new_code_str = compound_function_assertion_generator.visit(ast)
  #print new_code_str
  #with open(filename, 'w') as f:
  #  f.write(new_code_str)

# requires coan2 to be installed as "coan", or present in util
def get_preprocessor_lines(fn):
  try:
    p = subprocess.Popen(["coan", "directives", fn], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  except OSError as e:
    if e.errno == errno.ENOENT:
      p = subprocess.Popen(["util/coan", "directives", fn], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
      raise e
  out, err = p.communicate()
  return out

# gets typedefs and structure definitions as a string
def get_type_definitions(fn):
  class TypeDefinitionGrabber(c_generator.CGenerator):
    def visit_FileAST(self, n):
      s = ""
      for ext in n.ext:
        if type(ext) is c_ast.Typedef or (type(ext) is c_ast.Decl and type(ext.type) in [c_ast.Struct, c_ast.Union]):
          s += self.visit(ext) + ";\n"
      return s

  type_info_grabber = TypeDefinitionGrabber()
  return type_info_grabber.visit(ast)

def get_preamble(fn):
  return get_preprocessor_lines(fn) + "\n" + get_type_definitions(fn) + "\n"

type_info = ""

# requires tcc to be installed as "tcc", or present in util
csizeof_cache_dict = {}
def csizeof(v, use_tcc=True, use_cache=True, include_dirs=[]):
  try_gcc_fallback = False
  if type(v) not in [list, str, tuple]:
    v = str(v)

  if type(v) in [list, tuple]:
    as_tuple = tuple(v)
    v = " ".join(v)
  elif type(v) is str:
    as_tuple = tuple([e.strip() for e in v.split(" ")]) # TODO handle all whitespace chars, not just " "

  # void type, regardless of any modifiers
  if "void" in [e.strip() for e in v.split(" ")]:
    return 0

  # look up in the cache to see if it's there
  if use_cache and as_tuple in csizeof_cache_dict:
    return csizeof_cache_dict[as_tuple]

  sz = None
  if "c_" + v in dir(ctypes):
    exec("ctypes_type = ctypes.c_" + v)
    sz = ctypes.sizeof(ctypes_type)
    if use_cache:
      csizeof_cache_dict[as_tuple] = sz
    return sz
    #if v in dir(ctypes):
    #  return ctypes.sizeof(v)
  # if "void" or "unsigned void" don't try to do sizeof, which only works with
  # GCC extensions and returns 1 - it carries ZERO information flow, so the size we want is 0 (bits)

  # including the main file might work because it gives us all custom typedefs, but it means too long compile time: an optimization should be just to include all preprocessor directives/macros and all type and struct/union definitions
  #cprog = "int main() { return sizeof(" + str(v) + "); }"
  #cprog = "#include <stdio.h>\nint main() { printf(\"%d\", sizeof(" + str(v) + ")); return 0; }"
  #cprog = "#include <stdio.h>\n#include \"" + filename + "\" int main() { printf(\"%d\", sizeof(" + str(v) + ")); return 0; }"
  cprog = "#include <stdio.h>\n" + type_info + "\nint main() { printf(\"%d\", sizeof(" + str(v) + ")); return 0; }"
  # try running tcc command in the shell or in the current directory, falling back to the one assumed to be provided in util
  try:
    p = subprocess.Popen(["tcc", "-run", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  except OSError as e:
    if e.errno == errno.ENOENT:
      p = subprocess.Popen(["util/tcc", "-Iutil/include", "-run", "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
      raise e
    
  out, err = p.communicate(input=cprog)
  try:
    sz = int(out)
  except:
    try_gcc_fallback = True
  if err:
    try_gcc_fallback = True
  if try_gcc_fallback:
    print("USING GCC FALLBACK")
    tmp_filename = filename + "_" + fn + ".out"
    p = subprocess.Popen(["gcc", "-o", tmp_filename], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.communicate(input=cprog)
    out, err = p.communicate(input=cprog)
    sz = int(out)
    if err:
      print err,
      sz = -1
  if use_cache:
    csizeof_cache_dict[as_tuple] = sz
  return sz

def get_fn_retval_name(fn_name):
  return "~~retval~~" + fn_name

def get_return_label_string():
  return "__return_label"

# This one is on function DECLARATIONS, even for functions that don't have corresponding definitions
class FuncDeclVisitor(c_ast.NodeVisitor):
  def visit_FuncDecl(self, node):
    print("declared name: " + str(fn_name))
    # do something with param list
    # do something with type/ptr decl
    fn_name = None # TODO should be a more general identifier, possibly nested like in CBMC
    type_name = None
    if type(node.type) is c_ast.TypeDecl:
      fn_name = node.type.declname
      # if native type, it's easy, no special library required
      try:
        #print " ".join(node.type.type.names)
        type_name = " ".join(node.type.type.names)
        sz = csizeof(type_name)
      except AttributeError as e:
        print "error:", e
        sz = -1
      # else, we need to do extra work, possibly including all our current types in the dummy-file
    elif type(node.type) is c_ast.PtrDecl:
      fn_name = node.type.type.declname
      # all pointers are the same size, so ignore the subtree
      #sz = ptr_sz
      #type_name = node.type.type.declname
      type_name = "void*"
      sz = csizeof(type_name)
      #sz = csizeof(ctypes.c_void_p, False)
    else:
      fn_name = None
    fn_name_retval = get_fn_retval_name(fn_name)
    v = VarInfo(name=fn_name_retval, size=sz, type_name=type_name)
    if fn_name:
      if fn_name in fn_ret_val_size_dict:
        if fn_ret_val_size_dict[fn_name] != v:
          raise Exception("function " + fn_name + " shouldn't already be in the name to retval size dict (well, possibly there once already because the header declared but didn't define), possibly duplicate declaration/definition? (got different size than was already there)")
      else:
        fn_ret_val_size_dict[fn_name] = v
      #print fn_ret_val_size_dict
      # now, we have a declared function to return size mapping, let's do the same for fun to param sizes
      vs = []
      if node.args:
        for param in node.args.params:
          type_name = None
          var_size = -1
          if type(param.type) == c_ast.TypeDecl:
            try:
              if type(param.type.type) is c_ast.Struct:
                type_name = "struct " + param.type.type.name
              elif type(param.type.type) is c_ast.Union:
                type_name = "union " + param.type.type.name
              else:
                type_name = " ".join(param.type.type.names)
              var_size = csizeof(type_name)
            except AttributeError as e:
              print "error:", e
          elif type(node.type) == c_ast.PtrDecl:
            type_name = "void*"
            var_size = csizeof(type_name)
          elif type(node.type) == c_ast.TypeDecl:
            if type(param.type) is c_ast.PtrDecl:
              type_name = "void*"
              var_size = csizeof(type_name)
            else:
              raise Exception("a type, " + str(param.type) + ", that I haven't handled yet has been encountered")
          # now add the new var to the dict
          vs.append(VarInfo(name=param.name, size=var_size, type_name=type_name))
      if fn_name:
        if fn_name in fn_params_dict:
          if fn_params_dict[fn_name] != vs:
            raise Exception("function " + fn_name + " shouldn't already be in the name to params size dict (well, possibly there once already because the header declared but didn't define), possibly duplicate declaration/definition? (got different size than was already there)")
        else:
          fn_params_dict[fn_name] = vs

# This is only for DEFINED functions, not just declared
class FuncDefVisitor(c_ast.NodeVisitor):
  def visit_FuncDef(self, node):
    # do something with param list
    # do something with type/ptr decl
    fn_name = node.decl.name
    print("defined name: " + str(fn_name))
    node = node.decl.type
    type_name = None
    if type(node.type) is c_ast.TypeDecl:
      # if native type, it's easy, no special library required
      try:
        #print " ".join(node.type.type.names)
        type_name = " ".join(node.type.type.names)
        sz = csizeof(type_name)
      except AttributeError as e:
        print "error:", e
        sz = -1
      # else, we need to do extra work, possibly including all our current types in the dummy-file
    elif type(node.type) is c_ast.PtrDecl:
      # all pointers are the same size, so ignore the subtree
      #sz = ptr_sz
      type_name = "void*"
      sz = csizeof(type_name)
      #sz = csizeof(ctypes.c_void_p, False)
    fn_name_retval = get_fn_retval_name(fn_name)
    v = VarInfo(name=fn_name_retval, size=sz, type_name=type_name)
    if fn_name:
      if fn_name in fn_ret_val_size_dict:
        if fn_ret_val_size_dict[fn_name] != v:
          raise Exception("function " + fn_name + " shouldn't already be in the name to retval size dict (well, possibly there once already because the header declared but didn't define), possibly duplicate declaration/definition? (got different size than was already there)")
      else:
        fn_ret_val_size_dict[fn_name] = v
      #print fn_ret_val_size_dict
      # now, we have a declared function to return size mapping, let's do the same for fun to param sizes
      vs = []
      if node.args:
        for param in node.args.params:
          type_name = None
          var_size = -1
          if type(param.type) == c_ast.TypeDecl:
            try:
              if type(param.type.type) is c_ast.Struct:
                type_name = "struct " + param.type.type.name
                var_size = csizeof(type_name)
              elif type(param.type.type) is c_ast.Union:
                type_name = "union " + param.type.type.name
                var_size = csizeof(type_name)
              else:
                type_name = " ".join(param.type.type.names)
                var_size = csizeof(type_name)
            except AttributeError as e:
              print "error:", e
          elif type(node.type) == c_ast.PtrDecl:
            type_name = "void*"
            var_size = csizeof(type_name)
          elif type(node.type) == c_ast.TypeDecl:
            if type(param.type) is c_ast.PtrDecl:
              type_name = "void*"
              var_size = csizeof(type_name)
            else:
              #raise Exception("a type, " + str(param.type) + ", that I haven't handled yet has been encountered")
              # TODO potentially incorrect if sizeof actually works on arrays, and it doesn't just mean pointer size
              type_name = "void*"
              var_size = csizeof(type_name)
          # now add the var
          vs.append(VarInfo(name=param.name, size=var_size, type_name=type_name))
      if fn_name:
        if fn_name in fn_params_dict:
          if fn_params_dict[fn_name] != vs:
            raise Exception("function " + fn_name + " shouldn't already be in the name to params size dict (well, possibly there once already because the header declared but didn't define), possibly duplicate declaration/definition? (got different size than was already there)")
        else:
          fn_params_dict[fn_name] = vs


class FuncCallVisitor(c_ast.NodeVisitor):
  def visit_FuncCall(self, node):
    #name = node.name.name
    #coord = node.name.coord
    node.show()
    #indent = 0
    #print "%s called at %s, with args:" % (name, coord)
    #indent = 2
    #print " "*indent + " ".join([str(e) for e in node.args.exprs])
    ##print str(dir(node.args.exprs[0])) + "\n"

def decide_info_flow(unwind_limit=32, int_sz=-1, cbmc_timeout=None, modelcounter_timeout=None):
  global options, fn_info_flow_dict
  #tmp_cnf_filename = tmpdir + "/TEMP.cnf"
  
  print("We're starting our info flow measurement.")
  if int_sz == -1:
    int_sz = csizeof("int")
  if int_sz not in [16, 32, 64]:
    int_sz = 32
  if type(modelcounter_timeout) in [int, float, long]:
    modelcounter_timeout = long(round(float(modelcounter_timeout)/1000)) # convert to seconds from millis
  print("We got the variable size: " + str(int_sz))
  if not options.decide_all_functions:
    if options.function not in fn_info_flow_dict:
      print("error: function name supplied to arguments does not exist in specified program!! Switching to doing all functions")
      options.decide_all_functions = True
    #assert(options.function in fn_info_flow_dict)
    reduced_info_flow_dict = {}
    reduced_info_flow_dict[options.function] = fn_info_flow_dict[options.function]
    fn_info_flow_dict = reduced_info_flow_dict
  
  re_to_match = re.compile("(__return_value)![0-9]+@[0-9]+#[0-9]+")
  #re_to_match_whole_line = re.compile("\s*c\s*[a-zA-Z_0-9]+::[0-9]+::(__return_value)![0-9]+@[0-9]+#[0-9]+")
  tmp_cnf_filename_template = os.path.split(filename)[1] + "_"
  tmp_cnf_filename_template_re = re.compile(os.path.split(filename)[1] + "_" + "[a-zA-Z0-9_]+")
  #tmp_cnf_filename_template_re = re.compile("\s*c\s*[a-bA-Z_0-9]+::[0-9]+::(__return_value)![0-9]+@[0-9]+#[0-9]+")
  if options.model_count_only:
    print("model-count-only mode specified, skipping CNF generation")
    if len(fn_info_flow_dict) == 0: # find possible function names from standard CNF format
      new_filename = filename.split(".cnf")[0]
      if len(new_filename.split("_", 1)) > 1:
        fn_name = new_filename.split("_", 1)[1]
        fn_info_flow_dict[fn_name] = 0
      else:
        possible_filenames = [possible_filename for possible_filename in os.listdir(os.path.split(filename)[0]) if tmp_cnf_filename_template_re.search(possible_filename)]
        for possible_filename in possible_filenames:
          fn_name = possible_filename.split(".cnf")[0].split("_")[1]
          fn_info_flow_dict[fn_name] = 0
  else:
    print("We're about to try running cbmc for the following dictionary of functions:")
    print(fn_info_flow_dict)
  for fn in fn_info_flow_dict:
    tmp_cnf_filename = os.path.split(filename)[0] + os.path.sep + tmp_cnf_filename_template + fn + ".cnf"
    # Generate a CNF with CBMC
    if not options.model_count_only:
      args = [filename, "--" + str(int_sz), "--function", fn, "--dimacs"]
      #args = [filename, "--" + str(int_sz), "--function", fn, "--dimacs", "--unwind", str(unwind_limit)]
      #args = [filename, "--" + str(int_sz), "--function", fn, "--dimacs", "--slice-formula", "--ignore-nonauto-assertions", "--print-assertion-literals", "--unwind", str(unwind_limit)] # ah right, vanilla cbmc doesn't have "--ignore-nonauto-assertions", "--print-assertion-literals", or "--havoc"
      # if use_havoc:
        # args.append("--havoc")
      args.extend(["--outfile", tmp_cnf_filename])
      print("We're about to try running cbmc for function " + str(fn) + " with the following args:")
      print(args)
      try:
        p = subprocess.Popen(["cbmc"] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      except OSError as e:
        if e.errno == errno.ENOENT:
          p = subprocess.Popen(["util/cbmc"] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
        else:
          raise e
      # if using the py3.3 subprocess backport, we have timeout available
      if options.use_py33_subprocess and cbmc_timeout is not None:
        try:
          out, err = p.communicate(timeout=cbmc_timeout)
        except TimeoutExpired:
          p.kill()
          out, err = p.communicate()
      else:
        out, err = p.communicate()
      if options.verbosity.print_cbmc_out:
        print out
      if options.verbosity.print_cbmc_err:
        print err
      
      print("We got our CNF: ")
      # We have our CNF - now it's time to run allsat on it and gather learned
      # clauses

    # first, we need to know which variables to do allsat on:
    allsat_vars = None
    def get_allsat_vars(cnffile):
      # search for __return_value!i@j#k, and assume only k changes (should be true if there's only a single function converted to single return point named __return_value
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
    if options.cnf_only:
      print("cnf-only argument is set, skipping model counting, cnf is " + tmp_cnf_filename)
    else:
      if not os.path.exists(tmp_cnf_filename):
        tmp_cnf_filename = filename
      
    with open(tmp_cnf_filename, "r") as cnffile:
      allsat_vars = get_allsat_vars(cnffile)

    if not allsat_vars: # if None or empty
      print("warning: did not receive literals on which to do #sat from cbmc procedure, maybe it was simplified out? skipping #sat solving")
      #print "fatal error: did not receive literals on which to do #sat from cbmc procedure, quitting before doing #sat solving"
      #exit(1)
    elif not options.model_count_only:
      rename_to_lits = range(1, len(allsat_vars)+1)
      cnftools_rename.rename_literals(tmp_cnf_filename, allsat_vars, rename_to_lits)
      allsat_vars = rename_to_lits

    # now we have to run the approximate #SAT
    
    # check if scope lines already exist
    with open(tmp_cnf_filename, "r") as cnffile:
      for line in cnffile:
        if line.startswith(APPROX_MC):
          lits = [int(e.strip()) for e in line.split(APPROX_MC)[1].split() if int(e.strip()) != 0]
          for l in lits:
            wrote_in_allsat_var_projection_scope[APPROX_MC].add(l)
        if line.startswith(APPROX_MC_PY):
          lits = [int(e.strip()) for e in line.split(APPROX_MC_PY)[1].split() if int(e.strip()) != 0]
          for l in lits:
            wrote_in_allsat_var_projection_scope[APPROX_MC_PY].add(l)
    try:
      with open(tmp_cnf_filename + ".scope", "r") as scopefile:
        lits = [int(e.strip()) for e in scopefile.readlines()]
        for l in lits:
          wrote_in_allsat_var_projection_scope[SHARPCDCL].add(l)
    except:
      pass
    # first, add the c ind lines for scalmc
    with open(tmp_cnf_filename, "a") as cnffile:
      i = 0
      approxmc_allsat_vars = [e for e in allsat_vars if e not in wrote_in_allsat_var_projection_scope[APPROX_MC]]
      while i < len(approxmc_allsat_vars):
        tokens = approxmc_allsat_vars[i:i+10]
        if len(tokens) > 0:
          print("c ind " + " ".join([str(v) for v in tokens]) + " 0")
          cnffile.write("c ind " + " ".join([str(v) for v in tokens]) + " 0\n")
        for l in tokens:
          wrote_in_allsat_var_projection_scope[APPROX_MC].add(l)
        i += 10
      approxmc_py_allsat_vars = [e for e in allsat_vars if e not in wrote_in_allsat_var_projection_scope[APPROX_MC_PY]]
      if len(approxmc_py_allsat_vars) > 0:
        print("cr " + " ".join([str(v) for v in approxmc_py_allsat_vars]))
        cnffile.write("cr " + " ".join([str(v) for v in approxmc_py_allsat_vars]) + "\n")
      for l in approxmc_py_allsat_vars:
        wrote_in_allsat_var_projection_scope[APPROX_MC_PY].add(l)
    if len(wrote_in_allsat_var_projection_scope[SHARPCDCL]) == 0:
      with open(tmp_cnf_filename + ".scope", "w+") as scopefile:
        sharpcdcl_allsat_vars = [e for e in allsat_vars if e not in wrote_in_allsat_var_projection_scope[SHARPCDCL]]
        scopefile.write("\n".join([str(v) for v in sharpcdcl_allsat_vars]))
        for l in sharpcdcl_allsat_vars:
          wrote_in_allsat_var_projection_scope[SHARPCDCL].add(l)
      
          
    if not options.cnf_only:
      # now run the program
      args = [tmp_cnf_filename]
      try:
        p = subprocess.Popen(["scalmc"] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      except OSError as e:
        if e.errno == errno.ENOENT:
          p = subprocess.Popen(["util/scalmc"] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
        else:
          raise e
      # if using the py3.3 subprocess backport, we have timeout available
      if options.use_py33_subprocess and modelcounter_timeout is not None:
        try:
          out, err = p.communicate(timeout=modelcounter_timeout)
        except TimeoutExpired:
          proc.kill()
          out, err = p.communicate()
      else:
        out, err = p.communicate()
      if options.verbosity.print_modelcounter_out:
        print out
      if options.verbosity.print_modelcounter_err:
        print err
      
      [multiplier, power] = out.split("Number of solutions is:")[1].split(" x ")
      [base, exponent] = power.split("^")
      multiplier = int(multiplier)
      base = int(base)
      exponent = int(exponent)
      solutions = multiplier * base ** exponent
      info_flow = math.log(solutions, 2)
      fn_info_flow_dict[fn] = info_flow

# call this first
def show_func_decls():
  if not options.model_count_only:
    # populate parameter and return value sizes of each function
    #v = FuncDeclVisitor()
    v = FuncDefVisitor()
    v.visit(ast)

    # now the return value sizes are set up, we can populate our current best estimate
    # of function info flow by initializing it to the number of bits in the ret val of
    # each function - initially assume all assignments possible
    for fn in fn_ret_val_size_dict:
      flow = fn_ret_val_size_dict[fn].size
      if flow < 0:
        pass # TODO: handle error case
      elif flow == 0:
        pass # just don't include it - 0 info flow such as void entries don't contribute to info flow
      else:
        fn_info_flow_dict[fn] = flow*8

  # now call the CBMC procedure, getting the number of solutions (2^(info_flow)) and get the corresp.
  # learned clauses
  decide_info_flow(cbmc_timeout=1000, modelcounter_timeout=1000)


  # finally, print out results
  if not options.cnf_only:
    print("Info flow results:\n" + "="*20)
    for entry in fn_info_flow_dict:
      print entry, ":", fn_info_flow_dict[entry]
    print("="*20)
  #print "Return value sizes:\n" + "="*20
  #for entry in fn_ret_val_size_dict:
  #  print entry, fn_ret_val_size_dict[entry]
  #print "\nParam sizes\n" + "="*20
  #for entry in fn_params_dict:
  #  print entry, fn_params_dict[entry]

def parse_file_build_if_needed(filename, use_cpp, cpp_args):
  global fakemake_includes
  ast = None
  done_parsing = False
  while not done_parsing:
    try:
      if options.fakemake:
        if fakemake_includes == []: # if we already resolved the deps, no need again
          deps = []
          #deps = fakemake.get_deps(filename) # MAKE SURE THIS IS UNCOMMENTED TO RUN THE MAKEFILE
          root_dir_of_program = fakemake.find_root_dir(filename)
          deps_list = []
          for d in deps:
            if len(d) > 0:
              if d[0] != os.path.sep: # if it's an absolute, not relative dir, i.e. /usr/lib/... then keep it absolute, if not then make it absolute
                d = os.path.abspath(os.path.join(root_dir_of_program, d))
              deps_list.append(d)
          deps_list.append(root_dir_of_program)
          fakemake_includes = deps_list
      cpp_args.extend(["-I" + i for i in fakemake_includes])
      #print("args to cpp after augmentation but before unique-ifying are:")
      #print(cpp_args)
      cpp_args = list(set(cpp_args)) # should maybe be careful about the order...
      #print("args to cpp after augmentation are:")
      # cpp_args.append("-D'__file__(x)='")
      # cpp_args.append("-D'__file(x)='")
      #print(cpp_args)
      ast = parse_file(filename, use_cpp=use_cpp, cpp_args=cpp_args)
      print("finished trying to parse the file")
      done_parsing = True
    except pycparser.plyparser.ParseError as e: # we couldn't do it with this parser, maybe there's a Makefile and simply including the dirs will work
      # ok, we don't have everything -- recursively try to fake define then parse:
      print(e.message)
      #print("appending " + "-D" + e.message.split("before: ")[1] + "=")
      cpp_args.append("-D" + e.message.split("before: ")[1] + "=")
  #ast = parse_file(filename, use_cpp=use_cpp, cpp_args=cpp_args) # final parse
  return ast

def main(argv):
  global ast, options, filename
  if len(argv) > 2:
    try:
      arg = argv[2].lower().strip()
      if not arg in ["-", "."] or int(arg, 0) == 0:
        options.function = argv[2]
        options.decide_all_functions = False
    except: pass
  
  if len(argv) > 3:
    try:
      arg = argv[3].lower().strip()
      if arg in ["true", "t"] or int(arg, 0) == 0:
        options.cnf_only = True
      elif not arg in ["false", "f", "0"] and not int(arg, 0) == 0:
        print("Invalid value " + argv[3] + " supplied for optional argument cnf-only, defaulting to \"false\".")
    except:
      pass
  
  if len(argv) > 4:
    both_modes_err_string = "Cannot specify both cnf-only and model-count-only modes"
    try:
      arg = argv[4].lower().strip()
      if arg in ["true", "t"] or int(arg, 0) == 0:
        if options.cnf_only:
          #print(both_modes_err_string)
          raise ValueError(both_modes_err_string)
          #options.cnf_only = False
          #options.model_count_only = False
        else:
          options.model_count_only = True
      elif not arg in ["false", "f", "0"] and not int(arg, 0) == 0:
        print("Invalid value " + argv[4] + " supplied for optional argument model-count-only, defaulting to \"false\".")
    except ValueError as e:
      if e.message == both_modes_err_string:
        raise e
  
  filename = argv[1]
  extra_include_dir = os.path.split(filename)[0] + "/include"
  assert(len(pycparser.__path__) == 1)
  include_dirs = [os.path.join(pycparser.__path__[0], "utils", "fake_libc_include"), "/usr/include", "/usr/share/gnulib/lib", os.path.abspath(os.path.join(os.path.split(filename)[0], "include"))]
  # include_dirs.append(include_dirs[-1] + "/cudd")
  # include_dirs.append("/usr/src/linux-headers-4.4.0-53/include")
  # include_dirs.append("/usr/src/linux-headers-4.4.0-53/include")
  include_dirs_strs = [r"-I" + d for d in include_dirs]
  # try:
  if not options.model_count_only:
    ast = parse_file_build_if_needed(filename, use_cpp=True, cpp_args=include_dirs_strs)
  # except pycparser.plyparser.ParseError, e:
    # gcc_pp_filename = filename + "_" + fn + ".gccp.c"
    # p = subprocess.Popen(["gcc", "-nostdint", "-o", gcc_pp_filename, "-E"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # p.communicate(input=cprog)
    # out, err = p.communicate(input=cprog)
    # "gcc -nostdinc -E -I/home/rg/pycparser-master/utils/fake_libc_include test.c > testPP.c"
    # print("oopsies")
    # exit(1)
    # raise e
  #old_ast = ast
  #ast = parse_file(filename, use_cpp=True, cpp_args=r"-Iutil/pycparser-master/utils/fake_libc_include/")
  new_filename = filename
  old_filename = filename
  if not options.model_count_only:
    new_filename = tmpdir + "/" + os.path.basename(filename)
    insert_assertions(ast, new_filename)
    ast = parse_file_build_if_needed(new_filename, use_cpp=True, cpp_args=include_dirs_strs)

    shutil.copy(old_filename, old_filename + ".BACKUP")
    shutil.copy(new_filename, old_filename)
  try:
    type_info = get_preamble(old_filename)
    show_func_decls()
  finally:
    if not options.model_count_only:
      shutil.copy(old_filename + ".BACKUP", old_filename)
  # filename = new_filename

  
  
  
  
  #convert_to_compound_function(old_ast, old_filename)

  #print "================\n"

if __name__ == "__main__":
  def usage_and_exit():
    print("usage: " + sys.argv[0] + " program [function] [cnf-only]")
    print("  program: a C source program")
    print("  function: a function over whose return variable to measure info-flow")
    print("            if omitted, measures info-flow for all functions in the C source specified in program")
    print("            using a value of - or . or 0 will omit and perform all-functions")
    print("  cnf-only: if \"1\" or \"true\", stops after CNF generation and does not perform model counting, default: false")
    exit(1)

  if len(sys.argv) < 2:
    usage_and_exit()
  
  main(sys.argv)
