"""
Copyright 2016 The OpenConfig Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


Extract information about paths in YANG data models

Notes:
- ignores rpcs and notification nodes

"""

import optparse
import sys
import os.path
import re

from pyang import plugin
from pyang import statements
from pyang import error


def pyang_plugin_init():
    plugin.register_plugin(PathPlugin())


class PathPlugin(plugin.PyangPlugin):

  def add_output_format(self, fmts):
    self.multiple_modules = True
    fmts['paths'] = self

  def add_opts(self, optparser):
    optlist = [
        optparse.make_option("--strip",
                              dest="strip_namespace",
                              action="store_true",
                              help="""Strip namespace prefixes from
                                path components"""),
        optparse.make_option("--opstate",
                              dest="opstate_paths",
                              action="store_true",
                              help="""Print list of operational state paths,
                              i.e., containing config:false leaves"""),
        optparse.make_option("--root",
                              dest="root_only",
                              action="store_true",
                              help="""List only root nodes (depth=1)"""),
        optparse.make_option("--no-errors",
                              dest="ignore_errors",
                              action="store_true",
                              help="""Try to ignore compilation errors"""),
        optparse.make_option("--include-keyword",
                              dest="include_keyword",
                              action="store_true",
                              help="""Display the type of node for each path,
                              e.g., leaf, container, etc."""),
        optparse.make_option("--print-depth",
                              dest="print_depth",
                              action="store_true",
                              help="""Display the tree depth of each path (root
                                is at depth [1]"""),
        optparse.make_option("--plain",
                              dest="print_plain",
                              action="store_true",
                              help="""Print only paths (useful with relocate
                                plugin"""),
        optparse.make_option("--for-relocate",
                              dest="relocate_output",
                              action="store_true",
                              help="""Generate paths output for use with relocate
                              plugin"""),
        optparse.make_option("--status",
                              dest="print_status",
                              action="store_true",
                              help="""Display status information for non-current nodes"""),
                ]
    g = optparser.add_option_group("paths output specific options")
    g.add_options(optlist)

  def emit(self, ctx, modules, fd):
    modulenames = [m.arg for m in modules]
    if not ctx.opts.ignore_errors:
      for (epos, etag, eargs) in ctx.errors:
        #
        #  When a module has not yet been parsed then the top.arg does
        #  not exist. This can be the case when an error is created early
        #  in the parsing process.
        #
        if not hasattr(epos.top, "arg"):
          raise error.EmitError("%s contains errors, and was not parsed"
              % (epos.ref))
        if (epos.top.arg in modulenames and
                  error.is_error(error.err_level(etag))):
            raise error.EmitError("%s contains errors" % epos.top.arg)
    emit_paths(ctx, modules, fd)


def emit_paths(ctx, modules, fd):

  ctx.opstate_paths = dict()
  for module in modules:
    children = [child for child in module.i_children]
    if children:
      if (not ctx.opts.print_plain and not ctx.opts.relocate_output):
        fd.write('\nmodule %s:\n' % module.i_modulename)
      elif ctx.opts.relocate_output:
        fd.write('\nmodule %s\n' % module.i_modulename)
      print_children(children, module, fd, ' ', ctx, 1)

  if ctx.opts.opstate_paths:
    fd.write('\nopstate paths (containing leaves):\n')
    for (opath, count) in ctx.opstate_paths.iteritems():
      fd.write(' %s : %d\n' % (opath, count))

  fd.write('\n')


def print_children(children, module, fd, prefix, ctx, level=0):
  for child in children:
    print_node(child, module, fd, prefix, ctx, level)


def print_node(node, module, fd, prefix, ctx, level=0):

  if node.keyword == 'rpc' or node.keyword == 'notification':
    return

  pathstr = statements.mk_path_str(node, True)
  if ctx.opts.strip_namespace:
    re_ns = re.compile(r'^.+:')

    path_components = [re_ns.sub('', comp) for comp in pathstr.split('/')]
    pathstr = '/'.join(path_components)

  # collect status information if there is a substatement
  status_stmnt = node.search_one('status')
  if status_stmnt is not None:
    status = status_stmnt.arg
  else:
    status = None;


  # annotate the leaf nodes only
  if node.keyword == 'leaf-list' or \
        (node.keyword == 'leaf' and not hasattr(node, 'i_is_key')):
    if node.i_config is True:
      config = "rw"
    else:
      config = "ro"
      if ctx.opts.opstate_paths:
        base = os.path.dirname(pathstr)
        if ctx.opstate_paths.get(base):
          ctx.opstate_paths[base] += 1
        else:
          ctx.opstate_paths[base] = 1
  else:
      config = None

  pathstr = get_pathstr(pathstr, config, status, ctx, level)

  fd.write(pathstr)

  if ctx.opts.include_keyword:
    fd.write(' [%s]' % node.keyword)

  fd.write('\n')

  if hasattr(node, 'i_children'):
    level += 1
    if ctx.opts.root_only:
      if level > 1:
        return
    if node.keyword in ['choice', 'case']:
        print_children(node.i_children, module, fd, prefix, ctx, level)
    else:
        print_children(node.i_children, module, fd, prefix, ctx, level)


def get_pathstr(pathstr, config, status, ctx, level):

  if ctx.opts.print_plain or ctx.opts.relocate_output:
    return pathstr

  s = ''
  if ctx.opts.print_depth:
    s += '  [%d]' % level
  else:
    s += '     '
  if config:
    s += '  [%s] %s' % (config, pathstr)
  else:
    s += '       %s' % (pathstr)

  if status and ctx.opts.print_status:
    s +='%s [%s]' % (s, status)

  return s
