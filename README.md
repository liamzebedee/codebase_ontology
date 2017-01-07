Codebase Ontologies
===================

 1. Download a Python codebase (like Tensorflow)
 2. `git clone https://github.com/liamzebedee/codebase_ontology`
 3. `python3 ../codebase_ontology [file or directory to analyse]`


End goal: (codebase, input_example) => relevant information to understand such an example.


Nodes:
 - ast.Module (tf)
 - ast.ClassDef (tf.Session)
 - ast.FunctionDef/AsyncFunctionDef (tf.Session.run)
 - ast.Global (tf._TENSOR_LIKE_TYPES)
 - ast.Nonlocal
 - Function Attribute (FLAGS in `./python/client/notebook.py`)
 - Expression Attribute (ie some_var.attribute)
 - ast.Name (`tensors_to_delete` in `tf.session.Session._register_dead_handle`)
 - ast.arg (`fetched_vals` in `tf.session.Session._get_indexed_slices_value_from_fetches`)
 - ast.keyword argument (`config` in `tf.session.BaseSession.__init__`)