"""
Copyright 2015 Google, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Extract documentation about elements in YANG data modules.

"""

import optparse
import sys
import os.path
import re
#from collections import OrderedDict
#from lxml import etree
import xml

from util.markdown_emitter import MarkdownEmitter
from util.html_emitter import HTMLEmitter
from util import yangpath
from util.yangdoc_defs import YangDocDefs
from pyang import plugin
from pyang import statements
from pyang import error

def pyang_plugin_init():
    plugin.register_plugin(DocsPlugin())


class DocsPlugin (plugin.PyangPlugin):

  def add_output_format (self, fmts):
    self.multiple_modules = True
    fmts['docs'] = self


  def add_opts(self, optparser):
    optlist = [
        optparse.make_option("--meta-only",
                              dest="meta_only",
                              action="store_true",
                              help="""Only produce documentation based on the
                              module metadata"""),
        optparse.make_option("--doc-format",
                              dest="doc_format",
                              action="store",
                              type="string",
                              default="markdown",
                              help="""Doc output format: markdown, html"""),
        optparse.make_option("--strip-ns",
                              dest="strip_namespace",
                              action="store_true",
                              help="""Strip namespace prefixes from
                                displayed paths"""),
        optparse.make_option("--no-structure",
                              dest="no_structure",
                              action="store_true",
                              help="""Do not generate docs for structure-only nodes (e.g., containers)"""),
        optparse.make_option("--doc-title",
                              dest="doc_title",
                              action="store",
                              type="string",
                              help="""Set the title of the output documentation page"""),
                ]
    g = optparser.add_option_group("docs output specific options")
    g.add_options(optlist)


  def emit(self, ctx, modules, fd):
    modulenames = [m.arg for m in modules]
    if not ctx.opts.ignore_errors:
      for (epos, etag, eargs) in ctx.errors:
          if (epos.top.arg in modulenames and
              error.is_error(error.err_level(etag))):
              raise error.EmitError("%s contains errors" % epos.top.arg)
    emit_docs(ctx, modules, fd)


class ModuleDoc:
  """This class serves as a container for a module's documentation.
  It includes the typedef and identity definitions and a reference to
  the top-level StatementDoc object (i.e., with the 'module' statement).
  """

  def __init__ (self, name):
    self.module_name = name

    # module is a reference to a StatementDoc object corresponding
    # to the top-level module
    self.module = None

    # identities contains a dict of
    # <identity name> : <StatementDoc object>
    self.identities = {}
    # base_identites stores a list of the base identity definitions
    # TODO: this does not support multi-level identity derivations
    self.base_identities = []

    # typedefs is a dict of the user-defined type definitions in
    # the module, each stored as a name:StatementDoc entry
    self.typedefs = {}

  def __str__ (self):
    # this is not particularly useful info in its current form --
    # primarily used for debugging
    s = "%s:\n" % self.module_name
    s += "  top-level elements: %d\n" % len(self.module.children)
    s += "  base identities: %d\n" % len(self.identities)
    s += "  type definitions: %d\n" % len(self.typedefs)

    return s

class TypeStatementDoc:
    """This class holds information about the types of an
    YANG element.  Compound types like unions may contain other
    types -- this class contains the hierarchy of types attached
    to a single StatementDoc object."""

    def __init__ (self, typename=None):

      self.typename = typename
      self.attrs = {}
      self.attrs['restrictions'] = {}
      self.childtypes = []

    def __str__(self):
      s = "type %s:\n" % self.typename

      for attr in self.attrs:
        s += "  %s : %s\n" % (attr, self.attrs[attr])

      if self.childtypes:
        s += "child types: "
        for child in self.childtypes:
          s += "%s: " % child.typename
        s += "\n"
        for child in self.childtypes:
          s += str(child)
        s += "\n"

      return s

class StatementDoc:
  """This class holds information about an element, i.e.
  a specific statement (e.g., leaf, container, list, etc.) The
  StatementDoc object is associated with its module"""

  def __init__ (self, name, keyword):
    self.name = name
    self.keyword = keyword

    # dict with attributes of the statements, e.g., description,
    # etc.
    self.attrs ={}

    # reference to the top-level type ojbect that stores types
    self.typedoc = None

    # list of child statements
    self.children = []

    # reference to the parent StatementDoc object of the current statement
    self.parent = None

    # reference to the ModuleDoc object that this statement belongs to
    self.module_doc = None

  def __str__ (self):
    # recursively prints the statement and its children -- primarily for
    # debugging
    s = "%s:\n" % self.name
    for attr in self.attrs:
      s += "  %s : %s\n" % (attr, self.attrs[attr])
    s += "parent: "
    if self.parent is not None:
      s += "%s:%s\n" % (self.parent.name, self.parent.type)
    else:
      s += "%s\n" % self.parent
    if self.children:
      s += "subs: "
      for child in self.children:
        s += "%s:%s " % (child.name, child.type)
      s += "\n"
      for child in self.children:
        s += str(child)
      s += "\n"

    return s


def emit_docs(ctx, modules, fd):
  """Top-level function to collect and print documentation"""
  ctx.mod_docs = []
  ctx.skip_keywords = []
  for module in modules:
    mod = collect_docs (module, ctx)
    ctx.mod_docs.append (mod)

  if ctx.opts.no_structure:
    ctx.skip_keywords = ['container', 'list']

  if ctx.opts.doc_format == "html":
    emitter = HTMLEmitter()
  else:
    emitter = MarkdownEmitter()
  # write top level module and types
  for mod in ctx.mod_docs:
    emitter.genModuleDoc(mod, ctx)
  # visit each child element recursively and write its docs
    for child in mod.module.children:
      emit_child (child, emitter, ctx, fd, 1)

  # emit docs for all of the current modules
  docs = emitter.emitDocs(ctx)

  fd.write(docs)

def emit_child (node, emitter, ctx, fd, level=1):

  emitter.genStatementDoc(node, ctx, level)

  if len(node.children) > 0:
    level += 1
  for child in node.children:
    emit_child (child, emitter, ctx, fd, level)

  # gen_docs_html(mod, ctx, fd)


def collect_docs(module, ctx):

  """Extract documentation for the supplied module -- module parameter is a
  pyang Statement object"""

  # create the top level container for this module
  modtop = ModuleDoc (module.i_modulename)

  # create the root StatementDoc object for the module
  mod = StatementDoc (module.i_modulename, module.keyword)
  modtop.module = mod

  # get the description text
  description = module.search_one ('description')
  mod.attrs['desc'] = description.arg

  # get the prefix used by the module
  mod.attrs['prefix'] = module.i_prefix

  # get the list of imported modules
  imports = module.search ('import')
  mod.attrs['imports'] = []
  for imp in imports:
    mod.attrs['imports'].append(imp.arg)
  # get the module version number if it exists
  # since this uses an extension in OpenConfig models,
  # must look for a keyword that is a tuple
  version = module.search_one(('openconfig-extensions','openconfig-version'))
  if version is not None:
    mod.attrs['version'] = version.arg
  # collect identities
  for (name, identity) in module.i_identities.iteritems():
    collect_identity_doc (identity, modtop)
  # collect typedefs
  for (name, typedef) in module.i_typedefs.iteritems():
    collect_typedef_doc (typedef, modtop)
  # collect elements
  for child in module.i_children:
    collect_child_doc (child, mod, modtop)

  return modtop

def collect_identity_doc (identity, mod):
  """Collect documentation fields for YANG identities"""
  id = StatementDoc (identity.arg, identity.keyword)
  desc = identity.search_one ('description')
  if desc is not None:
    id.attrs['desc'] = desc.arg
  base = identity.search_one ('base')
  if base is not None:
    # this is derived identity
    id.attrs['base'] = base.arg
  else:
    # this is a base identity
    id.attrs['base'] = None
    mod.base_identities.append(id.name)
  reference = identity.search_one('reference')
  if reference is not None:
    id.attrs['reference'] = reference.arg
  # add the identity to the module object
  mod.identities[id.name] =  id

def collect_typedef_doc (typedef, mod):
  """Collect documentation fields for YANG typedefs"""
  td = StatementDoc (typedef.arg, typedef.keyword)
  desc = typedef.search_one ('description')
  if desc is not None:
    td.attrs['desc'] = desc.arg

  for p in YangDocDefs.type_leaf_properties:
    prop = typedef.search_one(p)
    if prop is not None:
      td.attrs[p] = prop.arg

  typest = typedef.search_one ('type')
  if typest is not None:
    typedoc = TypeStatementDoc ()
    td.typedoc = typedoc
    collect_type_docs(typest, typedoc)
  # add the typedef to the module object
  mod.typedefs[td.name] =  td

def collect_child_doc (node, parent, top):
  """Collect documentation fields for a statement.  node
  is a PYANG statement object, while parent is a ModuleDoc
  or StatementDoc object. top is the top level ModuleDoc
  object"""

  statement = StatementDoc (node.arg, node.keyword)
  statement.parent = parent
  statement.module_doc = top
  parent.children.append(statement)

  # fill in some attributes if they exist

  # type information
  type = node.search_one ('type')
  if type is not None:
    # create the Type object
    statement.typedoc = TypeStatementDoc()
    collect_type_docs(type, statement.typedoc)

  # node description
  desc = node.search_one ('description')
  if desc is not None:
    statement.attrs['desc'] = desc.arg

  # reference statement
  reference = node.search_one('reference')
  if reference is not None:
    statement.attrs['reference'] = reference.arg

  # default statement
  default = node.search_one('default')
  if default is not None:
    statement.attrs['default'] = default.arg

  # schema path for the current node
  path = statements.mk_path_str(node, True)
  statement.attrs['path'] = path

  # rw or ro info
  if hasattr(node, 'i_config'):
    statement.attrs['config'] = node.i_config

  # list keys
  if hasattr(node, 'i_is_key'):
    statement.attrs['is_key'] = node.i_is_key
  else:
    statement.attrs['is_key'] = False

  # collect data from children, i.e., depth-first
  if hasattr (node, 'i_children'):
    for child in node.i_children:
      collect_child_doc (child, statement,top)

def collect_type_docs (typest, typedoc):
  """Given a pyang type statement object, populates information
  about the type in the TypeStatementDoc object.  Some types may
  require recursive resolution for compound types, e.g.,
  unions, enumeration"""

  typedoc.typename = typest.arg
  if typest.arg == 'identityref':
    # base must be set for an identityref type
    base = typest.search_one ('base')
    typedoc.attrs['base'] = base.arg
  elif typest.arg == 'enumeration':
    # collect the enums into a dict of enumvalue:description
    typedoc.attrs['enums'] = {}
    enums = typest.search('enum')
    for enum in enums:
      enumdesc = enum.search_one('description')
      # generally expect a description substatement, but it might be None
      typedoc.attrs['enums'][enum.arg] = enumdesc.arg
  elif typest.arg == 'leafref':
    ref_path = typest.search_one('path')
    typedoc.attrs['leafref_path'] = yangpath.strip_namespace(ref_path.arg)
  elif typest.arg == 'string':
    pattern = typest.search_one('pattern')
    if pattern:
      typedoc.attrs['restrictions']['pattern'] = pattern.arg
  elif typest.arg in YangDocDefs.integer_types:
    rng = typest.search_one('range')
    if rng:
      typedoc.attrs['restrictions']['range'] = rng.arg
  elif typest.arg == 'union':
    # collect member types of the union
    types = typest.search('type')
    for type in types:
      # create a new typedoc
      utype = TypeStatementDoc(type.arg)
      typedoc.childtypes.append(utype)
      collect_type_docs (type, utype)

  # TODO: should probably collect substatements as they are usually
  # restrictions on the value, which are useful to document.




