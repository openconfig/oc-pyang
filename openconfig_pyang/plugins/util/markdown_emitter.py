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


Implements a Markdown documentation emitter for YANG modules

"""

from .doc_emitter import DocEmitter
import yangpath
from . import markdown_helper

class MarkdownEmitter(DocEmitter):


  def genModuleDoc(self, mod, ctx):
    md = markdown_helper.MarkdownHelper()

    # emit top level module info
    s = md.h1(mod.module_name) + "\n"
    s += md.h3("Description") + "\n"
    s += "\n" + mod.module.attrs['desc'] + "\n"

    # handle typedefs
    if len(mod.typedefs) > 0:
      s += md.h3(md.b("Types")) + "\n"
      for (typename, td) in mod.typedefs.iteritems():
        s += md.h4(typename) + "\n"
        s += "\n" + md.b("type") + ": " +  td.attrs['type'] + "\n"
        s += "\n" + md.i("description:") + "<br />\n"
        s += "\n" + td.attrs['desc'] + "\n"

    # handle identities
    if len(mod.identities) > 0:
      s += md.h3(md.b("Identities")) + "\n"
      for base_id in mod.base_identities:
        s += md.h4("base: " + md.i(base_id)) + "\n"
        s += "\n" + mod.identities[base_id].attrs['desc'] + "\n"
        # collect all of the identities that have base_id as
        # their base
        derived = { key:value for key,value in mod.identities.items() if value.attrs['base'] == base_id }
        # emit the identities derived from the current base
        for (idname, id) in derived.iteritems():
          s += md.h4(idname) + "\n"
          s += "\n" + md.b("base identity") + ": " +  id.attrs['base'] + "\n"
          s += "\n" + md.i("description:") + "<br />\n"
          s += "\n" + id.attrs['desc'] + "\n"

    if len(mod.module.children) > 0:
      s+= md.h3(md.b("Data nodes")) + "\n"

    return s


  def genStatementDoc(self, statement, ctx, level=1):
    """Markdown emitter method for YANG statements"""

    s = ""
    md = markdown_helper.MarkdownGen()

    if ctx.opts.strip_namespace:
      pathstr = yangpath.strip_namespace(statement.attrs['path'])
    else:
      pathstr = statement.attrs['path']

    # for 'skipped' nodes, just print the path
    if statement.keyword in self.path_only:
      s += md.h4(md.b(pathstr)) + "\n"
      return s

    s += md.h4(md.b(statement.name)) + "\n"
    s += md.b("nodetype") + ": " + statement.keyword
    if statement.attrs['is_key']:
      s+= " (list key)"
    s +=  "\n"
    if statement.attrs.has_key('type'):
      if (statement.attrs['type'] == 'identityref'):
        s += "\n" + md.b("type") + ": " +  statement.attrs['type'] + " " + statement.attrs['base'] + "\n"
      else:
        s += "\n" + md.b("type") + ": " +  statement.attrs['type'] + "\n"
    s += "\n" + md.b("path") + ": " +  pathstr + "\n"
    if statement.attrs.has_key('desc'):
      s += "\n" + md.i("description:") + "<br />\n"
      s += statement.attrs['desc'] + "\n"
    return s
