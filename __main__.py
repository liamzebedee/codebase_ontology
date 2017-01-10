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


dir_from_where_script_is_called = os.getcwd()

def _identity(obj):
    return obj

if sys.version_info < (3, 0):
    import codecs
    _open_with_encoding = codecs.open
    # codecs.open doesn't translate newlines sadly.
    def _from_system_newlines(input):
        return input.replace("\r\n", "\n")
    def _to_system_newlines(input):
        if os.linesep != "\n":
            return input.replace("\n", os.linesep)
        else:
            return input
else:
    _open_with_encoding = open
    _from_system_newlines = _identity
    _to_system_newlines = _identity


class RefactoringTool(object):
    def __init__(self, options=None, explicit=None):
        self.logger = logging.getLogger("RefactoringTool")
        self.fixer_log = []
        self.wrote = False
        self.files = []  # List of files that were or should be modified


        # Our stuff
        self.func_calls = {}
        self.graph = nx.Graph()
        self.named_graph_nodes = {} # name => id


    def refactor(self, items, write=False, doctests_only=False):
        """Refactor a list of files and directories."""
        for dir_or_file in items:
            if os.path.isdir(dir_or_file):
                self.refactor_dir(dir_or_file, write, doctests_only)
            else:
                self.refactor_file(dir_or_file, write, doctests_only)

    def refactor_dir(self, dir_name, write=False, doctests_only=False):
        """Descends down a directory and refactor every Python file found.
        Python files are assumed to have a .py extension.
        Files and subdirectories starting with '.' are skipped.
        """
        py_ext = os.extsep + "py"
        for dirpath, dirnames, filenames in os.walk(dir_name):
            dirnames.sort()
            filenames.sort()
            for name in filenames:
                if (not name.endswith('_test.py') and not name.startswith(".") and
                    os.path.splitext(name)[1] == py_ext):
                    fullname = os.path.join(dirpath, name)

                    # TODO fix this
                    # module_path = os.path.relpath(fullname, start=dir_from_where_script_is_called)
                    # print(module_path + '\n')
                    # return
                    
                    self.refactor_file(fullname, write, doctests_only)
            # Modify dirnames in-place to remove subdirs with leading dots
            dirnames[:] = [dn for dn in dirnames if not dn.startswith(".")]

    def _read_python_source(self, filename):
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
        with _open_with_encoding(filename, "r", encoding=encoding) as f:
            return _from_system_newlines(f.read()), encoding

    def refactor_file(self, filename, write=False, doctests_only=False):
        """Refactors a file."""
        input, encoding = self._read_python_source(filename)
        if input is None or input == '':
            # Reading the file failed.
            return
        input += "\n" # Silence certain parse errors
        
        tree = self.refactor_string(input, filename)

        _, module_name = os.path.split(filename)

        parse_ast_into_graph(tree, self.graph, module_name)
        
        # func_calls = get_func_calls(tree)

        # for call in func_calls:
        #     self.func_calls[call] = self.func_calls.get(call, 0) + 1


    def refactor_string(self, data, name):
        """Refactor a given input string.
        Args:
            data: a string holding the code to be refactored.
            name: a human-readable name for use in error/log messages.
        Returns:
            An AST corresponding to the refactored input stream; None if
            there were errors during the parse.
        """
        tree = None

        try:
            tree = ast.parse(data)
        except Exception as err:
            print("Error parsing %s" % name)

        return tree



class FuncCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self._name = deque()

    @property
    def name(self):
        return '.'.join(self._name)

    @name.deleter
    def name(self):
        self._name.clear()

    def visit_Name(self, node):
        self._name.appendleft(node.id)

    def visit_Attribute(self, node):
        try:
            self._name.appendleft(node.attr)
            self._name.appendleft(node.value.id)
        except AttributeError:
            self.generic_visit(node)



def get_func_calls(tree, depth=1):
    func_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword):
            print(node.arg)

        if isinstance(node, ast.Call):
            callvisitor = FuncCallVisitor()
            callvisitor.visit(node.func)
            func_calls.append(callvisitor.name)

    return func_calls

def get_top_100_calls(rt):
    call_stats = rt.func_calls
    sorted_x = sorted(call_stats.items(), key=operator.itemgetter(1), reverse=True)
    for i in range(0, 100):
        print(sorted_x[i][0])

def get_stats(file_or_dir):
    rt = RefactoringTool()
    rt.refactor(items=[file_or_dir])
    return rt

def compare_two_files(file_or_dir1, file_or_dir2):
    codebase_rt = get_stats(file_or_dir1)
    example_rt = get_stats(file_or_dir2)

    for func in example_rt.func_calls:
        print(func, ' ', codebase_rt.func_calls.get(func, 0))

def check_some_stats():
    # print(rt.func_calls)
    # print(get_top_100_calls(rt))    
    pass

def generate_graph_node(module, _class, function, name):
    pass


# How we are going to do it:
# Traverse the graph from the leafs to the root
# For each import statement we encounter, IMPORT IT! and then get the .__file__ and analyse its source, running the same algorithm
# https://docs.python.org/3/library/inspect.html
# 


def parse_ast_into_graph(tree, graph, module_name, parent_graph_node=None):
    graph_node = None

    # Modules
    if isinstance(tree, ast.Module):
        # graph.add_node()

    for node in ast.iter_child_nodes(tree):
        # Classes
        if isinstance(node, ast.ClassDef):
            name = node.name

            print('[class] ', name)

            graph.add_node(name)

        # Functions
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            name = node.name
            print('[func] ', name)
            graph.add_node(name)

        # Globals/nonlocals
        elif isinstance(node, ast.Global) or isinstance(node, ast.Nonlocal):
            for name in node.names:
                print('[global] ', name)
                graph.add_node(name)

        # Attributes
        elif isinstance(node, ast.Attribute):
            name = node.attr
            print('[attr] ', name)
            graph.add_node(name)

        # Names
        elif isinstance(node, ast.Name):
            name = node.id
            
            if hasattr(__builtins__, name) or name == 'self' or name == '_':
                continue
            else:
                print('[name] ', name)
                graph.add_node(name)

        # Args
        elif isinstance(node, ast.arg):
            name = node.arg
            if name == 'self':
                continue

            print(name)
            graph.add_node(name)

            pass

        # Keyword args
        elif isinstance(node, ast.keyword):
            if hasattr(node, 'arg'):
                name = node.arg
                if name == 'self':
                    continue
            
                print(name)
                graph.add_node(name)
            pass

        parse_ast_into_graph(node, graph, module_name, parent_node=tree)


def gen_graph(file_or_dir):
    rt = RefactoringTool()
    rt.refactor(items=[file_or_dir])
    print(rt.graph.nodes())


auto_i = 0
def get_id():
    global auto_i
    auto_i += 1
    return auto_i

if __name__ == '__main__':
    import networkx as nx
    import argparse
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input file or dir', required=True)
    parser.add_argument('-i2', '--input2', help='2nd Input file or dir', required=False)
    args = parser.parse_args()

    file_or_dir1 = args.input
    file_or_dir2 = args.input2

    if file_or_dir2:
        compare_two_files(file_or_dir1, file_or_dir2)

    rt = gen_graph(file_or_dir1)
    






    

   









