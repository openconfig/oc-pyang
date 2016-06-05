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
from util import yangpath

INSTANTIATED_DATA_KEYWORDS = ['leaf', 'leaf-list', 'container', 'list',
                                'choice']

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


    # Add OpenConfig validation phase
    statements.add_validation_phase('preinit', before='init')

    # Add an expensive function which we call one per module to check
    # things that cannot be checked in the later phases (e.g., text
    # conventions).
    statements.add_validation_fun('preinit', ['module'],
      lambda ctx, s: v_preinit_module_checks(ctx, s))

    # add the OpenConfig validators

    # Check for all type statements
    statements.add_validation_fun(
      'type_2', ['type', 'identity', 'identityref'],
      lambda ctx, s: v_chk_octypes(ctx, s))

    # Checks module properties after the module has
    # been parsed
    statements.add_validation_fun(
      'type_2', ['module'],
      lambda ctx, s: v_chk_ocmodule(ctx, s))

    # Check for warnings that are style-guide specific
    statements.add_validation_fun(
      'type_2', ['presence', 'choice', 'feature', 'if-feature'],
      lambda ctx, s: v_styleguide_warnings(ctx, s))

    # Check properties that are related to data elements
    statements.add_validation_fun(
      'type_2', ['leaf', 'leaf-list', 'list', 'container'],
      lambda ctx, s: v_chk_data_elements(ctx, s))

    # Check grouping names
    statements.add_validation_fun(
      'type_2', ['container'],
      lambda ctx, s: v_chk_standard_grouping_naming(ctx, s))

    # Check the prefix of the module
    statements.add_validation_fun(
      'type_2', ['prefix'],
      lambda ctx, s: v_chk_prefix(ctx, s))

    # Checks relevant to placement of leaves and leaf lists within the
    # opstate structure
    statements.add_validation_fun(
      'reference_2', ['leaf', 'leaf-list'],
      lambda ctx, s: v_chk_opstate_paths(ctx,s))

    # Checks lists within the structure
    statements.add_validation_fun(
      'reference_4', ['list'],
      lambda ctx, s: v_chk_list_placement(ctx, s))

    # Checks relevant to the specifications of paths in the module
    statements.add_validation_fun(
      'reference_2', ['path', 'augment'],
      lambda ctx, s: v_chk_path_refs(ctx,s))

    # Check that leaves are mirrored between config and state containers
    statements.add_validation_fun(
      'reference_4', ['container'],
      lambda ctx, s: v_chk_leaf_mirroring(ctx,s))

    # add the OpenConfig error codes

    # capitalization of enumeration values
    error.add_error_code(
      'OC_ENUM_CASE', 3,
      'enum value' + ' "%s" should be all caps as "%s"')

    # UPPERCASE_WITH_UNDERSCORES required for enum values
    error.add_error_code(
      'OC_ENUM_UNDERSCORES', 3,
      'enum value ' + '"%s" should be of the form ' +
      'UPPERCASE_WITH_UNDERSCORES: "%s"')

    # capitalization of identity values
    error.add_error_code(
      'OC_IDENTITY_CASE', 3,
      'identity name' + ' "%s" should be all caps as "%s"')

    # UPPERCASE_WITH_UNDERSCORES required for identity values
    error.add_error_code(
      'OC_IDENTITY_UNDERSCORES', 3,
      'identity name ' + '"%s" should be of the form ' +
      'UPPERCASE_WITH_UNDERSCORES: "%s"')

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

    # a config leaf does not have a mirrored applied config leaf in the state
    # container
    error.add_error_code(
      'OC_OPSTATE_APPLIED_CONFIG', 3,
      '"%s" is not mirrored in the state container at %s')

    # a list is within a container that has elements other than the list within
    # it
    error.add_error_code(
      'OC_LIST_SURROUNDING_CONTAINER', 3,
      'List %s is within a container (%s) that has other elements ' +
          'within it: %s')

    # A list does not have an enclosing container
    error.add_error_code(
      'OC_LIST_NO_ENCLOSING_CONTAINER', 3,
      'List %s is directly within a config or state container (%s)')

    # a module defines data nodes at the top-level
    error.add_error_code(
      'OC_MODULE_DATA_DEFINITIONS', 3,
      'Module %s defines data definitions at the top level: %s')

    # a module is missing an openconfig-version statement
    error.add_error_code(
      'OC_MODULE_MISSING_VERSION', 3, 'Module %s is missing an ' +
      'openconfig-version statement')

    # a module uses the 'choice' keyword
    error.add_error_code(
      'OC_STYLE_AVOID_CHOICE', 4, 'Element %s uses the choice keyword, which ' +
        'should be avoided')

    # a module uses the 'presence' keyword
    error.add_error_code(
      'OC_STYLE_AVOID_PRESENCE', 4, 'Element %s uses the presence keyword, ' +
        'which should be avoided')

    # a module uses the 'if-feature' or 'feature' keyword
    error.add_error_code(
      'OC_STYLE_AVOID_FEATURES', 4, 'Element %s uses feature or if-feature ' +
        'which should be avoided')

    # invalid semantic version argument to openconfig-version
    error.add_error_code(
      'OC_INVALID_SEMVER', 3, 'Semantic version specified (%s) is invalid')

    # missing a revision statement that has a reference of the
    # current semantic version
    error.add_error_code(
      'OC_MISSING_SEMVER_REVISION', 4, 'Revision statement should contain' +
        'reference substatement corresponding to semantic version %s')

    # invalid data element naming
    error.add_error_code(
      'OC_DATA_ELEMENT_INVALID_NAME', 4, 'Invalid naming for element %s ' +
          'data elements should generally be lower-case-with-hypens')

    # the module uses an invalid form of prefix
    error.add_error_code(
      'OC_PREFIX_INVALID', 4, 'Prefix %s for module does not match the ' +
          'expected format - use the form oc-<shortdescription>')

    # the module is missing a standard grouping (e.g., -top)
    error.add_error_code(
      'OC_MISSING_STANDARD_GROUPING', 4, 'Module %s is missing a grouping suffixed ' +
        'with %s')

    # the module has a nonstandard grouping name
    error.add_error_code(
      'OC_GROUPING_NAMING_NONSTANDARD', 4, 'In container %s, grouping %s does not ' +
        'match standard naming - suffix with %s?')

    # key statements do not have quoted arguments
    error.add_error_code(
      'OC_KEY_ARGUMENT_UNQUOTED', 3, 'All key arguments of a list should be ' +
        'quoted (%s is not)')

def v_chk_octypes(ctx, statement):
  """
    Check individual types for compliance against OpenConfig rules.
    Particularly:
      * enumeration arguments should be in UPPERCASE_WITH_UNDERSCORES
      * identity names should be in UPPERCASE_WITH_UNDERSCORES
  """

  re_uc = re.compile(r'[a-z]')
  re_ucwithunderscore = re.compile(r'^[A-Z][0-9A-Z\_\.]+$')

  if (statement.arg == 'enumeration'):
    enums = statement.search('enum')
    for enum in enums:
      if re_uc.search(enum.arg):
        err_add(ctx.errors, statement.pos, 'OC_ENUM_CASE',
          (enum.arg, enum.arg.upper()))

      if not re_ucwithunderscore.match(enum.arg):
        err_add(ctx.errors, statement.pos, 'OC_ENUM_UNDERSCORES',
          (enum.arg, enum.arg.upper().replace("-", "_")))

  if (statement.keyword == 'identity'):
    if re_uc.search(statement.arg):
      err_add(ctx.errors, statement.pos, 'OC_IDENTITY_CASE',
        (statement.arg, statement.arg.upper()))

    if not re_ucwithunderscore.match(statement.arg):
      err_add(ctx.errors, statement.pos, 'OC_IDENTITY_UNDERSCORES',
        (statement.arg, statement.arg.upper().replace("-", "_")))

  if (statement.keyword == 'identityref'):
    base_stmt = statement.search_one('base')
    if base_stmt is not None:
      if not re_uc.search(base_stmt.arg):
        err_add(ctx.errors, statement.pos, 'OC_IDENTITY_CASE',
          (base_stmt.arg, base_stmt.arg.upper()))
      if not re_ucwithunderscore.match(base_stmt.arg):
        err_add(ctx.errors, statement.pos, 'OC_IDENTITY_UNDERSCORES',
          (base_stmt.arg, base_stmt.arg.upper()))

def v_chk_ocmodule(ctx, statement):
  """
    Check characteristics of an entire OpenConfig module.
    Particularly:
      * Module should include an "openconfig-extensions:openconfig-version"
        statement, which should match semantic versioning patterns.
      * Module should not define any data elements at the top level.
      * Module name should be "openconfig-".
  """

  data_definitions = [i.arg for i in statement.substmts if i.keyword in
                      INSTANTIATED_DATA_KEYWORDS]
  if len(data_definitions):
    err_add(ctx.errors, statement.pos, 'OC_MODULE_DATA_DEFINITIONS',
      (statement.arg, ", ".join(data_definitions)))

  version = None
  for s in statement.substmts:
    if isinstance(s.keyword, tuple) and s.keyword[1] == 'openconfig-version':
      version = s
  if version is None:
    err_add(ctx.errors, statement.pos, 'OC_MODULE_MISSING_VERSION',
      statement.arg)
    return

  if not re.match("^[0-9]+\.[0-9]+\.[0-9]+$", version.arg):
    err_add(ctx.errors, statement.pos, 'OC_INVALID_SEMVER',
      version.arg)

  match_revision = False
  for revision_stmt in statement.search('revision'):
    reference_stmt = revision_stmt.search_one('reference')
    if reference_stmt is not None and \
              reference_stmt.arg == version.arg:
      match_revision = True

  if match_revision is False:
    err_add(ctx.errors, statement.pos, 'OC_MISSING_SEMVER_REVISION',
      version.arg)

  top_groupings = []
  for grouping in statement.search('grouping'):
    if re.match(".*\-top$", grouping.arg):
      top_groupings.append(grouping.arg)
  if not len(top_groupings):
    err_add(ctx.errors, statement.pos, 'OC_MISSING_STANDARD_GROUPING',
      (statement.arg, "-top"))



def v_chk_opstate_paths(ctx, statement):
  """
    Check elements for compliance with the opstate structure. Called for leaves
    and leaf-lists.

    Particularly:
      * Skip checks for YANG list keys
      * Check that there is a single 'config' and 'state' container in the
        path
      * Check that elements in a 'config' container are r/w, and 'state' are ro
  """

  pathstr = statements.mk_path_str(statement, False)
  # print "examining path to %s: %s" % (statement.arg, pathstr)

  # leaves that are list keys are exempt from this check.  YANG
  # requires them at the top level of the list, i.e., not allowed
  # in a descendent container
  if statement.keyword == 'leaf' and hasattr(statement, 'i_is_key'):
    keytype = statement.search_one ('type')
    if keytype.arg != 'leafref':
      err_add(ctx.errors, statement.pos, 'OC_OPSTATE_KEY_LEAFREF',
        statement.arg)
    # print "leaf %s is a key, skipping" % statement.arg
    return

  #path_elements = [c.encode('ascii', 'ignore') for c in yangpath.split_paths(pathstr)]
  path_elements = yangpath.split_paths(pathstr)
  # count number of 'config' and 'state' elements in the path
  confignum = path_elements.count('config')
  statenum = path_elements.count('state')
  if confignum != 1 and statenum != 1:
    err_add(ctx.errors, statement.pos, 'OC_OPSTATE_CONTAINER_COUNT',
      (pathstr))

  # for elements in a config or state container, make sure they have the
  # correct config property
  if statement.parent.keyword == 'container':
    # print "%s %s in container: %s (%s)" % (statement.keyword, pathstr,
    #  str(statement.parent.arg), statement.i_config)
    if statement.parent.arg == 'config':
      if statement.i_config is False:
        err_add(ctx.errors, statement.pos, 'OC_OPSTATE_CONFIG_PROPERTY',
          (statement.arg, 'config', 'true'))
    elif statement.parent.arg == 'state' or statement.parent.arg == 'counters':
      if statement.i_config is True:
        err_add(ctx.errors, statement.parent.pos, 'OC_OPSTATE_CONFIG_PROPERTY',
          (statement.arg, 'state', 'false'))
    else:
      err_add(ctx.errors, statement.pos, 'OC_OPSTATE_CONTAINER_NAME',
      (statement.arg, pathstr))


def v_chk_leaf_mirroring(ctx, statement):
  """
    Check that all config leaves are included in the state container
  """

  # Skip the check if the container is not a parent of other containers
  if statement.search_one('container') is None:
    return

  containers = statement.search('container')
  # Only perform this check if this is a container that has both a config
  # and state container
  c_config, c_state = None, None
  for c in containers:
    if c.arg == 'config':
      c_config = c
    elif c.arg == 'state':
      c_state = c
    if not None in [c_config, c_state]:
      break

  if None in [c_config, c_state]:
    return

  config_elem_names = [i.arg for i in c_config.substmts
                          if not i.arg == 'config' and
                            i.keyword in INSTANTIATED_DATA_KEYWORDS]
  state_elem_names = [i.arg for i in c_state.substmts
                          if not i.arg == 'state' and
                            i.keyword in INSTANTIATED_DATA_KEYWORDS]

  for elem in config_elem_names:
    if not elem in state_elem_names:
      err_add(ctx.errors, statement.parent.pos, 'OC_OPSTATE_APPLIED_CONFIG',
        (elem, statements.mk_path_str(statement, False)))


def v_chk_path_refs(ctx, statement):
  """
    Check path references for absolute / relative paths as appropriate.
    This function is called with the following statements:
      * path
      * augment
  """
  path = statement.arg
  if path[0] == '/':
    abspath = True
  else:
    abspath = False
  components = yangpath.split_paths(path)
  # consider the namespace in the first component
  # assumes that if the namespace matches the module namespace, then
  # relative path should be used (intra-module )
  if ":" in components[0]:
    (namespace, barepath) = components[0].split(':')
  else:
    namespace = statement.i_module.i_prefix
    barepath = components[0]
  mod_prefix = statement.i_module.i_prefix
  if namespace == mod_prefix and abspath:
    err_add(ctx.errors, statement.pos, 'OC_RELATIVE_PATH',
      (statement.keyword, statement.arg))

def v_chk_list_placement(ctx, statement):
  """
    Check that lists are placed correctly in the structure.
    Particularly:
      * Check that the list has a surrounding container that does not
        have any other elements within it.
  """

  if statement.parent.arg in ["config", "state"]:
    err_add(ctx.errors, statement.parent.pos, 'OC_LIST_NO_ENCLOSING_CONTAINER',
      (statement.arg, statement.parent.arg))

  parent_substmts = [i.arg for i in statement.parent.substmts
                      if i.keyword in INSTANTIATED_DATA_KEYWORDS]
  if not parent_substmts == [statement.arg]:
    remaining_parent_substmts = [i.arg for i in statement.parent.substmts
                                  if not i.arg == statement.arg and i.keyword
                                    in INSTANTIATED_DATA_KEYWORDS]
    err_add(ctx.errors, statement.parent.pos, 'OC_LIST_SURROUNDING_CONTAINER',
      (statement.arg, statement.parent.arg,
        ", ".join(remaining_parent_substmts)))

def v_styleguide_warnings(ctx, statement):
  if statement.keyword == 'choice':
    err_add(ctx.errors, statement.pos, 'OC_STYLE_AVOID_CHOICE',
      (statement.arg))
  elif statement.keyword == 'presence':
    err_add(ctx.errors, statement.pos, 'OC_STYLE_AVOID_PRESENCE',
      (statement.parent.arg))
  elif statement.keyword == 'feature':
    err_add(ctx.errors, statement.pos, 'OC_STYLE_AVOID_FEATURES',
      (statement.arg))
  elif statement.keyword == 'if-feature':
    err_add(ctx.errors, statement.parent.pos, 'OC_STYLE_AVOID_FEATURES',
      (statement.parent.arg))

def v_chk_data_elements(ctx, statement):
  if not re.match("^[A-Za-z0-9\-]+$", statement.arg):
    err_add(ctx.errors, statement.pos, 'OC_DATA_ELEMENT_INVALID_NAME',
      statement.arg)

def v_chk_prefix(ctx, statement):
  if not re.match("^oc\-[a-z\-]+$", statement.arg) and \
        "openconfig-" in statement.arg:
    err_add(ctx.errors, statement.pos, 'OC_PREFIX_INVALID',
      statement.arg)

def v_chk_standard_grouping_naming(ctx, statement):

  # we don't want to check 'config' or 'state' containers
  if statement.arg in ['config', 'state']:
    return

  cfg_container, state_container = None, None
  containers = statement.search('container')
  for container in containers:
    if container.arg == "config":
      cfg_container = container
    elif container.arg == "state":
      state_container = container

def v_preinit_module_checks(ctx, statement):
  """
    Validation functions that can only be run against the raw
    YANG, prior to pyang parsing it. Some attributes of the
    text file get lost - for example, quotations.
  """

  handle = None
  for mod in ctx.repository.get_modules_and_revisions(ctx):
    if mod[0] == statement.arg:
      handle = mod

  if handle is not None:
    try:
      module = ctx.repository.get_module_from_handle(handle[2])
      module_lines = module[2].split("\n")
    except (AttributeError, IndexError) as e:
      sys.stderr.write("WARNING: could not correctly split module %s: %s\n" %
        (statement.arg, str(e)))

  else:
    sys.stderr.write("WARNING: could not locate module %s in open modules\n" % statement.arg)
    return

  key_re = re.compile("^([ ]+)key([ ]+)(?P<arg>.*);$")
  quoted_re = re.compile('^\".*\"$')

  ln_count = 0
  for l in module_lines:
    ln_count += 1
    l = l.rstrip("\n")
    if key_re.match(l):
      arg_part = key_re.sub('\g<arg>', l)
      if not quoted_re.match(arg_part):
        # Because we are not reading the file like pyang does, then
        # we do not have an existing position object, so fake one.
        pos = error.Position(statement.pos.ref)
        pos.line = ln_count
        err_add(ctx.errors, pos, 'OC_KEY_ARGUMENT_UNQUOTED', arg_part)
