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


Implements an HTML documentation emitter for YANG modules

"""
import os
import re

from xml.etree import ElementTree as ET
from jinja2 import Environment, FileSystemLoader
from doc_emitter import DocEmitter
from yangdoc_defs import YangDocDefs
import html_helper
import yangpath

class HTMLEmitter(DocEmitter):

  def genModuleDoc(self, mod, ctx):
    """HTML emitter for top-level module documentation given a
    ModuleDoc object"""

    ht = html_helper.HTMLHelper()

    # TODO: this is far too hardcoded
    mod_div = ht.open_tag("div", newline=True)

    # module name
    mod_div += ht.h1(mod.module_name, {"class": "module-name", "id": ("mod-" + ht.gen_html_id(mod.module_name))},2,True)

    if mod.module.attrs.has_key('version'):
      mod_div += ht.h4("openconfig-version: " + mod.module.attrs['version'], {"class": "module-header"},2,True)

    # module description header
    mod_div += ht.h4("Description", {"class": "module-desc-header"},2,True)

    # module description text
    paragraphs = text_to_paragraphs(mod.module.attrs['desc'])
    for para in paragraphs:
      mod_div += ht.para(para, {"class": "module-desc-text"},2,True)

    mod_div += ht.h4("Imports", {"class": "module-header"},2,True)
    mod_div += "<p class=\"module-desc-text\">"
    for i in mod.module.attrs['imports']:
      mod_div += "%s<br>\n" % i
    mod_div += "</p>\n"

    mod_div += ht.close_tag(newline=True)

    # initialize and store in the module docs
    self.moduledocs[mod.module_name] = {}
    self.moduledocs[mod.module_name]['module'] = mod_div
    self.moduledocs[mod.module_name]['data'] = ""

    # handle typedefs
    if len(mod.typedefs) > 0:
      types_div = ht.open_tag("div", newline=True)
      types_div += ht.h3("Defined types", {"class": "module-types-header", "id": mod.module_name + "-defined-types"},2,True)

      for (typename, td) in mod.typedefs.iteritems():
        types_div += ht.h4(typename,{"class": "module-type-name","id": "type-" + ht.gen_html_id(typename)},2,True)
        types_div += ht.para(ht.add_tag("span","description:" + ht.br(newline=True), {"class": "module-type-text-label"}) + td.attrs['desc'],{"class": "module-type-text"},2,True)
        types_div += gen_type_info(td.typedoc, 2)

        for prop in YangDocDefs.type_leaf_properties:
          if td.attrs.has_key(prop):
            types_div += ht.para(ht.add_tag("span", prop,{"class": "module-type-text-label"}) + ": " + td.attrs[prop],{"class": "module-type-text"},2,True)


      types_div += ht.close_tag(newline=True)
    else:
      # module doesn't have any typedefs
      types_div = ""

    # store the typedef docs
    self.moduledocs[mod.module_name]['typedefs'] = types_div

    # handle identities
    if len(mod.identities) > 0:
      idents_div = ht.open_tag("div", newline=True)
      idents_div += ht.h3("Identities", {"class": "module-types-header", "id": mod.module_name + "-identities"},2,True)

      for base_id in mod.base_identities:
        idents_div += ht.h4("base: " + base_id,{"class": "module-type-name","id":"ident-" + ht.gen_html_id(base_id)},2,True)
        idents_div += ht.para(ht.add_tag("span","description:" + ht.br(newline=True), {"class": "module-type-text-label"}) + mod.identities[base_id].attrs['desc'],{"class": "module-type-text"},2,True)

        # collect all of the identities that have base_id as
        # their base
        # TODO(aashaikh): this needs to be updated to handle nested identities / multiple inheritance
        derived = { key:value for key,value in mod.identities.items() if value.attrs['base'] == base_id }
        # emit the identities derived from the current base
        for (idname, id) in derived.iteritems():
          idents_div += ht.h4(idname,{"class": "module-type-name","id":"ident-" + ht.gen_html_id(idname)},2,True)
          idents_div += ht.para(ht.add_tag("span","description:",{"class": "module-type-text-label"}) + ht.br(newline=True) + id.attrs['desc'],{"class":"module-type-text"},2,True)
          idents_div += ht.para(ht.add_tag("span", "base identity: ",{"class": "module-type-text-label"})
            + ht.add_tag("a", id.attrs['base'],{"href":"#ident-"+ht.gen_html_id(id.attrs['base'])}),
            {"class":"module-type-text"},2,True)

        idents_div += ht.close_tag(newline=True)
    else:
      # module doesn't have any identities
      idents_div = ""

    # store the identity docs
    self.moduledocs[mod.module_name]['identities'] = idents_div

    gen_nav_tree(self, mod, 0)


  def genStatementDoc(self, statement, ctx, level=1):
    """HTML emitter for module data node given a StatementDoc
    object"""

    if ctx.opts.no_structure and statement.keyword in ctx.skip_keywords:
      return

    ht = html_helper.HTMLHelper()

    s_div = ht.open_tag("div", {"class":"statement-section"}, newline=True)

    if ctx.opts.strip_namespace:
      pathstr = yangpath.strip_namespace(statement.attrs['path'])
    else:
      pathstr = statement.attrs['path']

    # for 'skipped' nodes, just print the path
    if statement.keyword in self.path_only:
      s_div += ht.h4(pathstr,None,level,True)
      s_div += ht.close_tag(newline=True)
      return s_div

    # statement path and name
    (prefix, last) = yangpath.remove_last(pathstr)
    prefix_name = ht.add_tag("span", prefix + "/", {"class": "statement-path"})
    statement_name = prefix_name + ht.br(level,True) + statement.name
    s_div += ht.h4(statement_name, {"class": "statement-name","id":statement.attrs['id']},level,True)

    # node description
    if statement.attrs.has_key('desc'):
      s_div += ht.para(ht.add_tag("span", "description",{"class": "statement-info-label"}) + ":<br />" + statement.attrs['desc'],{"class": "statement-info-text"},level,True)
    s_div += ht.close_tag(newline=True)

    # check for additional properties
    notes = ""
    if statement.attrs['is_key']:
      notes += " (list key)"
    if statement.attrs['config']:
      notes += " (rw)"
    else:
      notes += " (ro)"
    keyword = statement.keyword + notes
    s_div += ht.para(ht.add_tag("span", "nodetype",{"class": "statement-info-label"}) + ": " + keyword,{"class": "statement-info-text"},level,True)
    # s_div += ht.para(ht.add_tag("span", "path",{"class":"statement-info-label"}) + ": " + pathstr,{"class":"statement-info-text"},level,True)

    # handle list nodes
    if statement.attrs['is_list']:
      list_keys = ""
      for key in statement.attrs['keys']:
        list_keys += " [" + ht.add_tag("a", key[0], {"href":"#" + key[1]}) + "]"
      s_div += ht.para(ht.add_tag("span", "list keys",{"class": "statement-info-label"}) + ": " + list_keys,{"class": "statement-info-text"},level,True)

    if statement.typedoc:
      s_div += gen_type_info(statement.typedoc, level)

    for prop in YangDocDefs.type_leaf_properties:
      if statement.attrs.has_key(prop):
        s_div += ht.para(ht.add_tag("span", prop, {"class": "statement-info-label"}) + ": " + statement.attrs[prop],{"class": "statement-info-text"},level,True)

    # add this statement to the collection of data
    self.moduledocs[statement.module_doc.module_name]['data'] += s_div

  def emitDocs(self, ctx, section=None):
    """Return the HTML output for all modules,
    or single section if specified"""

    ht = html_helper.HTMLHelper()

    docs = []
    navs = []
    navids = []
    # create the documentation elements for each module
    for module_name in self.moduledocs:
      # check if the module has no data nodes
      if 'data' not in self.moduledocs[module_name]:
        self.moduledocs[module_name]['data'] = ""
      else:
        # create the header for the data elements
        hdr = ht.h3("Data elements", {"class": "module-types-header", "id": module_name + "-data"},2,True)
        self.moduledocs[module_name]['data'] = hdr + self.moduledocs[module_name]['data']

      if section is not None:
        return self.moduledocs[module_name][section]
      else:
        docs.append(self.moduledocs[module_name]['module'] +
          self.moduledocs[module_name]['typedefs'] +
          self.moduledocs[module_name]['identities'] +
          self.moduledocs[module_name]['data'])
        navs.append(self.moduledocs[module_name]['navlist'])
        navids.append(self.moduledocs[module_name]['navid'])

    if ctx.opts.doc_title is None:
      # just use the name of the first module returned by the dict if no title
      # is supplied
      doc_title = self.moduledocs.iterkeys().next()
    else:
      doc_title = ctx.opts.doc_title

    s = populate_template (doc_title, docs, navs, navids)

    return s

def gen_type_info(typedoc, level=1):
  """Create and return documentation based on the type.  Expands compound
  types."""

  ht = html_helper.HTMLHelper()
  s = ""

  typename = typedoc.typename
  s += ht.para(ht.add_tag("span", "type",{"class": "statement-info-label"}) + ": " + typename,{"class": "statement-info-text"},level,True)

  if typename == 'enumeration':
    s += " "*level + "<ul>\n"
    for (enum, desc) in typedoc.attrs['enums'].iteritems():
      s += " "*level + "<li>" + enum + "<br />" + desc + "</li>\n"
    s += " "*level + "</ul>\n"
  elif typename == 'string':
    if typedoc.attrs['restrictions'].has_key('pattern'):
      s += " "*level + "<ul>\n"
      s += " "*level + "<li>pattern:<br>\n"
      s += " "*level + typedoc.attrs['restrictions']['pattern'] + "\n</li>\n"
      s += " "*level + "</ul>\n"
  elif typename in YangDocDefs.integer_types:
    if typedoc.attrs['restrictions'].has_key('range'):
      s += " "*level + "<ul>\n"
      s += " "*level + "<li>range:\n"
      s += " "*level + typedoc.attrs['restrictions']['range'] + "\n</li>\n"
      s += " "*level + "</ul>\n"
  elif typename == 'identityref':
    s += " "*level + "<ul>\n"
    s += " "*level + "<li>base: " + typedoc.attrs['base'] + "</li>\n"
    s += " "*level + "</ul>\n"
  elif typename == 'leafref':
    s += " "*level + "<ul>\n"
    s += " "*level + "<li>path reference: " + typedoc.attrs['leafref_path'] + "</li>\n"
    s += " "*level + "</ul>\n"
  elif typename == 'union':
    s += " "*level + "<ul>\n"
    for childtype in typedoc.childtypes:
      s += " "*level + gen_type_info(childtype)
    s += " "*level + "</ul>\n"
  else:
    pass

  return s


def populate_template(title, docs, navs, nav_ids):
  """Populate HTML templates with the documentation content"""

  template_path = os.path.dirname(__file__) + "/../templates"
  j2_env = Environment(loader=FileSystemLoader(template_path),
                        trim_blocks=True)
  template = j2_env.get_template('yangdoc.html')

  return template.render({'title': title,
                        'htmldocs': docs,
                        'menus': navs,
                        'menu_ids': nav_ids })

def gen_nav_tree(emitter, root_mod, level=0):
  """Generate a list structure to serve as navigation for the
  module.  root_mod is a top-level ModuleDoc object"""

  ht = html_helper.HTMLHelper()

  nav = "<ul id=\"%s\">\n" % ("tree-" + ht.gen_html_id(root_mod.module_name))

  # module link
  nav += "<li><a class=\"menu-module-name\" href=\"%s\">%s</a></li>\n" % ("#mod-" + ht.gen_html_id(root_mod.module_name), root_mod.module_name)

  # generate links for types and identities
  if len(root_mod.typedefs) > 0:
    nav += "<li><a href=\"%s\">%s</a>\n" % ("#" + ht.gen_html_id(root_mod.module_name) + "-defined-types", "Defined types")
    types = root_mod.typedefs.keys()
    nav += " <ul>\n"
    for typename in types:
      nav += "  <li><a href=\"%s\">%s</a></li>\n" % ("#type-"+ht.gen_html_id(typename), typename)
    nav += " </ul>\n"
    nav += "</li>\n"

  if len(root_mod.identities) > 0:
    nav += "<li><a href=\"%s\">%s</a>\n" % ("#" + ht.gen_html_id(root_mod.module_name) + "-identities", "Identities")
    nav += " <ul>\n"
    for base_id in root_mod.base_identities:
      derived = { key:value for key,value in root_mod.identities.items() if value.attrs['base'] == base_id }
      nav += "  <li><a href=\"%s\">%s</a>\n" % ("#ident-" + ht.gen_html_id(base_id), base_id)
      nav += "  <ul>\n"
      for idname in derived.keys():
        nav += "    <li><a href=\"%s\">%s</a></li>\n" % ("#ident-" + ht.gen_html_id(idname), idname)
      nav += "  </ul>\n"
      nav += "  </li>\n"
    nav += " </ul>\n"
    nav += "</li>\n"

  # generate links for data nodes
  top = root_mod.module
  level = 0
  # nav += "<li><a href=\"%s\">%s</a>\n" % ("#" + ht.gen_html_id(root_mod.module_name) + "-data", "Data elements")
  if len(top.children) > 0:
    nav += "<li><a href=\"#%s-data\">%s</a>\n" % (root_mod.module_name, "Data elements")
    nav += "<ul>\n"
    for child in top.children:
      nav += gen_nav (child, root_mod, level)
    nav += "</li>\n"
    nav += "</ul>\n"

  nav += "</ul>\n"

  # store the navigation list
  emitter.moduledocs[root_mod.module_name]['navlist'] = nav
  emitter.moduledocs[root_mod.module_name]['navid'] = "tree-" + ht.gen_html_id(root_mod.module_name)

  #modtop.nav += "</ul>"
  # top.nav += "<li>" + statement.name + "</li>\n"

def gen_nav(node, root_mod, level = 0):
  """Add the list item for node (StatementDoc object)"""

  # print "nav: %s %s (%d)" % (node.keyword, node.name, len(node.children))
  current_level = level
  nav = ""
  if len(node.children) > 0:
    # print the current node (opening li element)
    nav += " "*level + " <li>" + "<a href=\"#" + node.attrs['id'] + "\">" + node.name + "</a>\n"
    # start new list for the children
    nav += " "*level + " <ul>\n"
    level += 1
    for child in node.children:
      nav += gen_nav (child, root_mod, level)
    # close list of children
    nav += " "*current_level + " </ul>\n"
    nav += " "*current_level + "</li>\n"
  else:
    # no children -- just print the current node and return
    nav += " "*current_level + " <li>" "<a href=\"#" + node.attrs['id'] + "\">" + node.name + "</a>\n"

  return nav

def text_to_paragraphs(textblock):
  """Simple conversion of text into paragraphs based (naively) on blank
  lines -- intended to use with long, multi-paragraph descriptions"""

  paras = textblock.split("\n\n")
  return paras