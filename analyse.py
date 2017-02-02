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

from lib2to3.pgen2 import tokenize

import networkx as nx
import argparse
import os





class Parser(object):
	def __init__(self):
		pass

	def read_python_source(self, filename):
		"""
		Do our best to decode a Python source file correctly.
		"""
		try:
			f = open(filename, "rb")
		except OSError as err:
			self.log_error("Can't open %s: %s", filename, err)
			return None, None
		try:
			encoding = tokenize.detect_encoding(f.readline)[0]
		finally:
			f.close()
		with open(filename, "r", encoding=encoding) as f:
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

		# Go through the leaves of the tree
		

		print(astdump(tree, include_attributes=True))


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






