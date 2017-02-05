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

		print(nicedump(tree))


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


def nicedump(node):
	interesting_attrs = ['body', 'targets', 'target', 'id', 'value', 'arguments', 'args', 'value', 'func', 'returns', 'name', 'n', 'arg', 'left', 'right', 's']
	def _process(node, tablevel=1):
		indent = tablevel * '\t'
		indent2 = indent + '\t'

		if isinstance(node, ast.AST):
			fields = [(a, _process(b, tablevel+1)) for a, b in ast.iter_fields(node) if a in interesting_attrs]

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






