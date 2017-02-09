import ast
from collections import deque
import multiprocessing
import operator


from pprint import pprint
import os
import sys
import logging
import operator
import collections
import io
from itertools import chain

import networkx as nx
import argparse
import os





class Parser(object):
	def __init__(self):
		pass

	def read_python_source(self, filename):
		with open(filename, "r") as f:
			return f.read()

	def parse_file(self, filename):
		py_src = self.read_python_source(filename)
		if py_src is None or py_src == '':
			return
		py_src += "\n"
		
		tree = None

		try:
			tree = ast.parse(py_src)
		except Exception as err:
			print("Error parsing %s" % name)

		# print(nicedump(tree))
		process_ast(tree)


def astdump(node, annotate_fields=True, include_attributes=False):
	"""
	Return a formatted dump of the tree in *node*.  This is mainly useful for
	debugging purposes.  The returned string will show the names and the values
	for fields.  This makes the code impossible to evaluate, so if evaluation is
	wanted *annotate_fields* must be set to False.  Attributes such as line
	numbers and column offsets are not dumped by default.  If this is wanted,
	*include_attributes* can be set to True.
	"""
	def _format(node):
		if isinstance(node, ast.AST):
			fields = [(a, _format(b)) for a, b in ast.iter_fields(node)]
			rv = '%s(%s' % (node.__class__.__name__, ', '.join(
				('%s=%s' % field for field in fields)
				if annotate_fields else
				(b for a, b in fields)
			))
			if include_attributes and node._attributes:
				rv += fields and ', ' or ' '
				rv += ', '.join('%s=%s' % (a, _format(getattr(node, a)))
								for a in node._attributes)
			return rv + ')'
		elif isinstance(node, list):
			return '[%s]' % ', '.join(_format(x) for x in node)
		return repr(node)
	if not isinstance(node, ast.AST):
		raise TypeError('expected AST, got %r' % node.__class__.__name__)
	return _format(node)


def get_name_for_node(node):
	name = ''

	# Classes
	if isinstance(node, ast.ClassDef):
		name = node.name

	# Functions
	elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
		name = node.name

	# Globals/nonlocals
	elif isinstance(node, ast.Global) or isinstance(node, ast.Nonlocal):
		# for nname in node.names:
		pass

	# Attributes
	elif isinstance(node, ast.Attribute):
		name = node.attr

	# Names
	elif isinstance(node, ast.Name):
		if hasattr(__builtins__, name) or name == 'self' or name == '_':
			return
		name = node.id

	# Args
	elif isinstance(node, ast.arg):
		if name == 'self':
			return
		name = node.arg

	# Keyword args
	elif isinstance(node, ast.keyword):
		if hasattr(node, 'arg'):
			if name == 'self':
				return
			name = node.arg

	return name

def process_ast(tree):
	if not isinstance(tree, ast.AST):
		raise TypeError('expected AST, got %r' % tree.__class__.__name__)

	return process(tree, parent_named_node=None)

def process(node, parent_named_node=None):
	this_named_node = get_name_for_node(node)
	if not this_named_node:
		 this_named_node = parent_named_node
	else:
		print(this_named_node)
	children = get_children_for_node(node)
	if children:
		for child in get_children_for_node(node):
			process(child, parent_named_node=this_named_node)
	# if isinstance(node, ast.AST):
	# 	# fields = [(a, _process(b, tablevel+1)) for a, b in ast.iter_fields(node) if a in interesting_attrs]
	# 	# field for field in fields
	# 	return rv
	# elif isinstance(node, list):
	# 	return ('[%s\n'+indent+']') % '\n'.join(_process(x, tablevel+1) for x in node)
	# return repr(node)

def get_children_for_node(node):
	# for each attribute
	# if attribute is not None
	# if attribute is identifier -> make a link to the parent
	# else traverse all attributes
	# 	if attribute is list
	# 		process each item
	#   if attribute is singular
	children = []
	if isinstance(node, ast.Module):
		children = node.body
	if isinstance(node, ast.Expression):
		children = [node.body]
	if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
		children.append(node.args)
		children.extend(node.body)
		if node.returns:
			children.append(node.returns)
	if isinstance(node, ast.ClassDef):
		children.extend(node.bases)
		children.extend(node.keywords)
		children.extend(node.body)
	if isinstance(node, ast.Return):
		if node.value:
			children.append(node.value)
	if isinstance(node, ast.Delete):
		children.extend(node.targets)
	if isinstance(node, ast.Assign):# or isinstance(node, ast.AnnAssign):
		children.extend(node.targets)
		children.append(node.value)
	if isinstance(node, ast.AugAssign):
		children.append(node.target)
		children.append(node.value)
	if isinstance(node, ast.For) or isinstance(node, ast.AsyncFor):
		# (expr target, expr iter, stmt* body, stmt* orelse)
		children.append(node.target)
		children.extend(node.iter)
		children.extend(node.body)
		children.extend(node.orelse)
	if isinstance(node, ast.While):
		children.append(node.test)
		children.extend(node.body)
		children.extend(node.orelse)
	if isinstance(node, ast.If):
		# expr test, stmt* body, stmt* orelse
		children.append(node.test)
		children.extend(node.body)
		children.extend(node.orelse)
	if isinstance(node, ast.With) or isinstance(node, ast.AsyncWith):
		# withitem* items, stmt* body)
		children.extend(node.items)
		children.extend(node.body)
	if isinstance(node, ast.Raise):
		# (expr? exc, expr? cause)
		if(node.exc):
			children.append(node.exc)
		if(node.cause):
			children.append(node.cause)
	if isinstance(node, ast.Try):
		# (stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
		children.extend(node.body)
		children.extend(node.handlers)
		children.extend(node.orelse)
		children.extend(node.finalbody)
	if isinstance(node, ast.Assert):
		# (expr test, expr? msg)
		pass

	# Imports are a special case
	if isinstance(node, ast.Import):
		# (alias* names)
		pass
	if isinstance(node, ast.ImportFrom):
		# (identifier? module, alias* names, int? level)
		pass

	if isinstance(node, ast.Global) or isinstance(node, ast.Nonlocal):
		# (identifier* names)
		pass

	if isinstance(node, ast.Expr):
		children.append(node.value)

	if isinstance(node, ast.Pass) or isinstance(node, ast.Break) or isinstance(node, ast.Continue):
		pass


	if isinstance(node, ast.BoolOp):
		# values
		children.extend(node.values)
	if isinstance(node, ast.BinOp):
		children.extend([node.right, node.left])
	if isinstance(node, ast.UnaryOp):
		# operand
		children.append(node.operand)
	if isinstance(node, ast.Lambda):
		# arguments args, expr body
		childen.append('args')
		childen.append('args')
	if isinstance(node, ast.IfExp):
		# expr test, expr body, expr orelse
		children.append(node.test)
		children.append(node.body)
		children.append(node.orelse)
	if isinstance(node, ast.Dict):
		# (expr* keys, expr* values)
		children.extend(node.keys)
		children.extend(node.values)
	if isinstance(node, ast.Set):
		# Set(expr* elts)
		children.extend(node.elts)
	if isinstance(node, ast.ListComp) or isinstance(node, ast.SetComp):
		# expr elt, comprehension* generators
		children.append(node.elt)
		children.extend(node.generators)
	if isinstance(node, ast.DictComp):
		# expr key, expr value, comprehension* generators)
		children.append(node.value)
		children.extend(node.generators)
	if isinstance(node, ast.GeneratorExp):
		# (expr elt, comprehension* generators)
		children.append(node.elt)
		children.extend(node.generators)
	if isinstance(node, ast.Await) or isinstance(node, ast.YieldFrom):
		# value
		children.append(node.value)
	if isinstance(node, ast.Yield):
		# value?
		if node.value:
			children.append(node.value)
	if isinstance(node, ast.Compare):
		# expr left, cmpop* ops, expr* comparators)
		children.append(node.left)
		children.extend(node.comparators)
	if isinstance(node, ast.Call):
		# expr func, expr* args, keyword* keywords)
		children.append(node.func)
		children.extend(node.args)
		children.extend(node.keywords)
	# if isinstance(node, ast.FormattedValue):
		# FormattedValue(expr value, int? conversion, expr? format_spec)
		# children.append(node.value)
	# if isinstance(node, ast.JoinedStr):
		# values
		# children.extend(node.values)


	# Primitives
	 # | Num(object n) -- a number as a PyObject.
	 # | Str(string s) -- need to specify raw, unicode, etc?
	 # | Bytes(bytes s)
	 # | NameConstant(singleton value)
	 # | Ellipsis
	 # | Constant(constant value)

	if isinstance(node, ast.Attribute) or isinstance(node, ast.Subscript) or isinstance(node, ast.Starred):
		children.append(node.value)
		# (expr value, identifier attr, expr_context ctx)
		# Subscript(expr value, slice slice, expr_context ctx)
		# | Starred(expr value, expr_context ctx)


	# | Name(identifier id, expr_context ctx)
	if isinstance(node, ast.List) or isinstance(node, ast.Tuple):
		# (expr* elts, expr_context ctx)
		children.extend(node.elts)

	if isinstance(node, ast.Slice):
		# slice = Slice(expr? lower, expr? upper, expr? step)
		pass
	if isinstance(node, ast.ExtSlice):
	  # | ExtSlice(slice* dims)
	  pass
	if isinstance(node, ast.Index):
		children.append(node.value)

	# boolop = And | Or

	# operator = Add | Sub | Mult | MatMult | Div | Mod | Pow | LShift
	#              | RShift | BitOr | BitXor | BitAnd | FloorDiv

	# unaryop = Invert | Not | UAdd | USub

	# cmpop = Eq | NotEq | Lt | LtE | Gt | GtE | Is | IsNot | In | NotIn

	if isinstance(node, ast.comprehension):
		# (expr target, expr iter, expr* ifs, int is_async)
		children.append(node.target)
		children.append(node.iter)
		children.extend(node.ifs)

	if isinstance(node, ast.excepthandler):
		if node.type:
			children.append(node.type)
		children.extend(node.body)
		# excepthandler = ExceptHandler(expr? type, identifier? name, stmt* body)
		# attributes (int lineno, int col_offset)
	if isinstance(node, ast.arguments):
		children.extend(node.args)
		children.extend(node.kwonlyargs)

		if node.vararg:
			children.append(node.vararg)
		if node.kwarg:
			children.append(node.kwarg)
		
		children.extend(node.kw_defaults)
		children.extend(node.defaults)

		# (arg* args, arg? vararg, arg* kwonlyargs, expr* kw_defaults,
			 # arg? kwarg, expr* defaults)
	if isinstance(node, ast.arg):
		pass
		# (identifier arg, expr? annotation)
		# attributes (int lineno, int col_offset)
	if isinstance(node, ast.keyword):
		# (identifier? arg, expr value)
		children.append(node.value)

	# TODO will have to handle this.
	if isinstance(node, ast.alias):
		# -- import name with optional 'as' alias.
		# alias = (identifier name, identifier? asname)
		pass

	if isinstance(node, ast.withitem):
		# (expr context_expr, expr? optional_vars)
		children.append(node.context_expr)
		if node.optional_vars:
			children.append(node.optional_vars)

	return children

identifier_field_names = ['id', 'name', 'module', 'attr', 'arg', 'asname']
def nicedump2(tree):
	def recurse(node):
		ids = [id_ for field_name, val in ast.iter_fields(node) if field_name in identifier_field_names]
		print(ids)
		get_children_for_node(node)

	recurse(tree)


def nicedump(node):
	interesting_attrs = ['body', 'targets', 'target', 'id', 'value', 'arguments', 'args', 'value', 'func', 'returns', 'name', 'n', 'arg', 'left', 'right', 's']

	def _process(node, tablevel=1):
		indent = tablevel * '\t'
		indent2 = indent + '\t'

		if isinstance(node, ast.AST):
			fields = [(a, _process(b, tablevel+1)) for a, b in ast.iter_fields(node) if a in interesting_attrs]
			# for fn,fv in fields:
				# if fn == 'id':
				# print(fn, fv.__class__)

			rv = '\n' + indent + node.__class__.__name__ + '\n'+indent2 + ('\n'+indent2).join('%s=%s' % field for field in fields)

			return rv
		elif isinstance(node, list):
			return ('[%s\n'+indent+']') % '\n'.join(_process(x, tablevel+1) for x in node)
		return repr(node)

	if not isinstance(node, ast.AST):
		raise TypeError('expected AST, got %r' % node.__class__.__name__)
	return _process(node)


auto_i = 0
def get_id():
	global auto_i
	auto_i += 1
	return auto_i

if __name__ == '__main__':
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('-i', '--input', help='Input file or dir', required=True)
	args = arg_parser.parse_args()
	
	starter_file = args.input
	parser = Parser()
	parser.parse_file(starter_file)






