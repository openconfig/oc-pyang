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


Check YANG modules for OpenConfig style and coding conventions.

This checker is derived from the standard pyang lint plugin which also checks
modules according the YANG usage guidelines in RFC 6087.
"""

import optparse
import sys
import os.path
import re

from pyang import plugin
from pyang import statements
from pyang import error
from pyang.error import err_add
from pyang.plugins import lint
from util import pathtree

def pyang_plugin_init():
  plugin.register_plugin(OpenConfigPlugin())

class OpenConfigPlugin(lint.LintPlugin):

  def __init__(self):
    lint.LintPlugin.__init__(self)
    self.modulename_prefixes = ['openconfig']

  def add_opts(self, optparser):
    optlist = [
          optparse.make_option("--openconfig",
                                dest="openconfig",
                                action="store_true",
                                help="""Validate the module(s) according to
                                OpenConfig conventions"""),
          optparse.make_option("--oc-only",
                                dest="openconfig_only",
                                action="store_true",
                                help="""Do not include standard lint (RFC 6087)
                                checking"""),
          ]
    g = optparser.add_option_group("OpenConfig specific options")
    g.add_options(optlist)

  def setup_ctx(self, ctx):
    if not (ctx.opts.openconfig):
      return
    if (not ctx.opts.openconfig_only):
      # call the standard linter setup
      self._setup_ctx(ctx)
    else:
      # don't call standard linter but have to set up some of the same rules
      # ourselves
      statements.add_validation_fun(
        'grammar', ['module', 'submodule'],
        lambda ctx, s: lint.v_chk_module_name(ctx, s, self.modulename_prefixes))

      error.add_error_code(
            'LINT_BAD_MODULENAME_PREFIX', 4,
            'RFC 6087: 4.1: '
            + 'no module name prefix used, suggest %s-%s')

    # add the OpenConfig validators

    statements.add_validation_fun(
      'type_2', ['type'],
      lambda ctx, s: v_chk_octypes(ctx, s))

    statements.add_validation_fun(
      'reference_2', ['leaf', 'leaf-list'],
      lambda ctx, s: v_chk_opstate_paths(ctx,s))

    statements.add_validation_fun(
      'reference_2', ['path, augment'],
      lambda ctx, s: v_chk_path_refs(ctx,s))

    # add the OpenConfig error codes

    # capitalization of enum values
    error.add_error_code(
      'OC_ENUM_CASE', 3,
      'enum value' + ' "%s" should be all caps as "%s"')

    # single config / state container in the path
    error.add_error_code(
      'OC_OPSTATE_CONTAINER_COUNT', 3,
      'path "%s" should have a single "config" or "state" component')

    # leaves should be in a 'config' or 'state' container
    error.add_error_code(
      'OC_OPSTATE_CONTAINER_NAME', 3,
      'element "%s" at path "%s" should be in a "config" or "state" container')

    # list keys should be leafrefs to respective value in config / state
    error.add_error_code(
      'OC_OPSTATE_KEY_LEAFREF', 3,
      'list key "%s" should be type leafref with a reference to corresponding' +
      ' leaf in config or state container')

    # leaves in in config / state should have the correct config property
    error.add_error_code(
      'OC_OPSTATE_CONFIG_PROPERTY', 3,
      'element "%s" is in a "%s" container and should have config value %s')

    # references to nodes in the same module / namespace should use relative
    # paths
    error.add_error_code(
      'OC_RELATIVE_PATH', 4,
      '"%s" path reference "%s" is intra-module but uses absolute path')

  # def post_validate(self, ctx, modules):

  #   for module in modules:
  #     children = [child for child in module.i_children]

def v_chk_octypes (ctx, statement):
  # check OpenConfig rules for relevant types

  # enum values should be all caps
  if (statement.arg == 'enumeration'):
    re_uc = re.compile(r'[a-z]')
    enums = statement.search('enum')
    for enum in enums:
      if re_uc.search(enum.arg):
        err_add (ctx.errors, statement.pos, 'OC_ENUM_CASE',
          (enum.arg, enum.arg.upper()))

def v_chk_opstate_paths(ctx, statement):
  # check OpenConfig rules for operational state modeling conventions

  pathstr = statements.mk_path_str(statement, False)
  # print "examining path to %s: %s" % (statement.arg, pathstr)

  # leaves that are list keys are exempt from this check.  YANG
  # requires them at the top level of the list, i.e., not allowed
  # in a descendent container
  if statement.keyword == 'leaf' and hasattr(statement, 'i_is_key'):
    keytype = statement.search_one ('type')
    if keytype.arg != 'leafref':
      err_add (ctx.errors, statement.pos, 'OC_OPSTATE_KEY_LEAFREF',
        statement.arg)
    # print "leaf %s is a key, skipping" % statement.arg
    return

  #path_elements = [c.encode('ascii', 'ignore') for c in pathtree.split_paths(pathstr)]
  path_elements = pathtree.split_paths(pathstr)
  # count number of 'config' and 'state' elements in the path
  confignum = path_elements.count('config')
  statenum = path_elements.count('state')
  if confignum != 1 and statenum != 1:
    err_add (ctx.errors, statement.pos, 'OC_OPSTATE_CONTAINER_COUNT',
      (pathstr))

  # for elements in a config or state container, make sure they have the
  # correct config property
  if statement.parent.keyword == 'container':
    # print "%s %s in container: %s (%s)" % (statement.keyword, pathstr,
    #  str(statement.parent.arg), statement.i_config)
    if statement.parent.arg == 'config':
      if statement.i_config is False:
        err_add (ctx.errors, statement.pos, 'OC_OPSTATE_CONFIG_PROPERTY',
          (statement.arg, 'config', 'true'))
    elif statement.parent.arg == 'state':
      if statement.i_config is True:
        err_add (ctx.errors, statement.parent.pos, 'OC_OPSTATE_CONFIG_PROPERTY',
          (statement.arg, 'state', 'false'))
    else:
      err_add (ctx.errors, statement.pos, 'OC_OPSTATE_CONTAINER_NAME',
      (statement.arg, pathstr))

def v_chk_path_refs(ctx, statement):
  """Check path references for absolute / relative paths as appropriate.
  This function is called with the following statements:
    path
    augment
  """
  path = statement.arg
  if path[0] == '/':
    abspath = True
  else:
    abspath = False
  components = pathtree.split_paths(path)
  # consider the namespace in the first component
  # assumes that if the namespace matches the module namespace, then
  # relative path should be used (intra-module )
  (namespace, barepath) = component[0].split(':')
  mod_prefix = statement.i_module.i_prefix
  if namespace == mod_prefix and abspath:
    err_add(ctx.errors, statement.pos, 'OC_RELATIVE_PATH',
      statement.keyword, statement.arg)



