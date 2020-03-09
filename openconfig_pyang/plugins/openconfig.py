"""Copyright 2016 The OpenConfig Authors.

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

from __future__ import print_function, unicode_literals

import re
from enum import IntEnum
import optparse
import os.path
from pyang import error
from pyang import plugin
from pyang import statements
from pyang.error import err_add
from pyang.plugins import lint


from util import yangpath

# Keywords which result in data nodes being created in a YANG tree
INSTANTIATED_DATA_KEYWORDS = [u"leaf", u"leaf-list", u"container", u"list",
                              u"choice"]
LEAFNODE_KEYWORDS = [u"leaf", u"leaf-list"]

# YANG types that should not be used in OpenConfig models.
BAD_TYPES = [u"empty", u"bits"]


class ErrorLevel(IntEnum):
  """An enumeration of the Pyang error levels.

     - Critical errors are those that are fatal for parsing.
     - Major errors are used as those that cannot be suppressed, and
       should result in the module failing submission checks.
     - Minor errors are used as those that can be suppressed, if there
       is a clear reason to break a convention.
     - Warnings are simply statements that the user should be aware of
       and should not result in submission failures.
  """
  CRITICAL = 1
  MAJOR = 2
  MINOR = 3
  WARNING = 4


class ModuleType(IntEnum):
  """An enumeration describing the type of module.

    OCINFRA: A model that does not need to be validated.
    NONOC: A non-OpenConfig model.
    OC: An OpenConfig model.
  """
  OCINFRA = 1
  NONOC = 2
  OC = 3


class ExternalValidationRules(object):
  """Definitions of the validation rules that should be applied
  from external sources - e.g., RFC6087.
  """

  required_substatements = {
      "module": (("contact", "organization", "description", "revision"),
                 "RFC 6087: 4.7"),
      "submodule": (("contact", "organization", "description", "revision"),
                    "RFC 6087: 4.7"),
      "revision": (("reference",), "RFC 6087: 4.7"),
      "extension": (("description",), "RFC 6087: 4.12"),
      "feature": (("description",), "RFC 6087: 4.12"),
      "identity": (("description",), "RFC 6087: 4.12"),
      "typedef": (("description",), "RFC 6087: 4.11,4.12"),
      "grouping": (("description",), "RFC 6087: 4.12"),
      "augment": (("description",), "RFC 6087: 4.12"),
      "rpc": (("description",), "RFC 6087: 4.12"),
      "notification": (("description",), "RFC 6087: 4.12,4.14"),
      "container": (("description",), "RFC 6087: 4.12"),
      "leaf": (("description",), "RFC 6087: 4.12"),
      "leaf-list": (("description",), "RFC 6087: 4.12"),
      "list": (("description",), "RFC 6087: 4.12"),
      "choice": (("description",), "RFC 6087: 4.12"),
      "anyxml": (("description",), "RFC 6087: 4.12"),
  }


def pyang_plugin_init():
  """
  Register the OpenConfig plugin with pyang.
  """
  plugin.register_plugin(OpenConfigPlugin())


class OpenConfigPlugin(lint.LintPlugin):
  """Plugin for Pyang to validate OpenConfig style guide conventions."""

  def __init__(self):
    lint.LintPlugin.__init__(self)
    self.modulename_prefixes = ["openconfig"]

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
    g = optparser.add_option_group(optparse.OptionGroup(optparser, "OpenConfig specific options"))
    g.add_options(optlist)

  def setup_ctx(self, ctx):
    if not ctx.opts.openconfig:
      return
    if not ctx.opts.openconfig_only:
      # Support IETF as a prefix for modules
      self.modulename_prefixes.extend(["ietf", "iana"])

      # We do not want all RFC6087 rules, so we need to borrow some
      # from the standard linter. We cannot simply call the _setup_ctx
      # module as this adds rules that we do not want - this code block
      # is borrowed from that module.
      statements.add_validation_var(
          "$chk_default",
          lambda keyword: keyword in lint._keyword_with_default)
      statements.add_validation_var(
          "$chk_required",
          lambda keyword: keyword in
          ExternalValidationRules.required_substatements)

      statements.add_validation_var(
          "$chk_recommended",
          lambda keyword: keyword in lint._recommended_substatements)

      statements.add_validation_fun(
          "grammar", ["$chk_default"],
          lambda ctx, s: lint.v_chk_default(ctx, s))
      statements.add_validation_fun(
          "grammar", ["$chk_required"],
          OCLintStages.openconfig_override_base_linter)
      statements.add_validation_fun(
          "grammar", ["$chk_recommended"],
          OCLintStages.openconfig_override_base_linter)

      statements.add_validation_fun(
          "grammar", ["namespace"],
          lambda ctx, s: lint.v_chk_namespace(ctx, s,
                                              self.namespace_prefixes))

      statements.add_validation_fun(
          "grammar", ["module", "submodule"],
          lambda ctx, s:
          lint.v_chk_module_name(ctx, s, self.modulename_prefixes))

      statements.add_validation_fun(
          "strict", ["include"],
          lambda ctx, s: lint.v_chk_include(ctx, s))

      # Register the default linter error codes
      error.add_error_code(
          "LINT_EXPLICIT_DEFAULT", ErrorLevel.WARNING,
          "RFC 6087: 4.3: "
          "statement \"%s\" is given with its default value \"%s\"")
      error.add_error_code(
          "LINT_MISSING_REQUIRED_SUBSTMT", ErrorLevel.MINOR,
          "%s: "
          "statement \"%s\" must have a \"%s\" substatement")
      error.add_error_code(
          "LINT_MISSING_RECOMMENDED_SUBSTMT", ErrorLevel.WARNING,
          "%s: "
          "statement \"%s\" should have a \"%s\" substatement")
      error.add_error_code(
          "LINT_BAD_NAMESPACE_VALUE", ErrorLevel.WARNING,
          "RFC 6087: 4.8: namespace value should be \"%s\"")
      error.add_error_code(
          "LINT_BAD_MODULENAME_PREFIX_1", ErrorLevel.WARNING,
          "RFC 6087: 4.1: "
          "the module name should start with the string %s")
      error.add_error_code(
          "LINT_BAD_MODULENAME_PREFIX_N", ErrorLevel.WARNING,
          "RFC 6087: 4.1: "
          "the module name should start with one of the strings %s")
      error.add_error_code(
          "LINT_NO_MODULENAME_PREFIX", ErrorLevel.WARNING,
          "RFC 6087: 4.1: "
          "no module name prefix string used")
      error.add_error_code(
          "LINT_BAD_REVISION", ErrorLevel.MINOR,
          "RFC 6087: 4.6: "
          "the module's revision %s is older than "
          "submodule %s's revision %s")
      error.add_error_code(
          "LINT_TOP_MANDATORY", ErrorLevel.MINOR,
          "RFC 6087: 4.9: "
          "top-level node %s must not be mandatory")
      error.add_error_code(
          "LONG_IDENTIFIER", ErrorLevel.MINOR,
          "RFC 6087: 4.2: identifier %s exceeds %s characters")

    # Add a pre-initialisation phase where we can read the
    # modules before they have been parsed by pyang fully.
    statements.add_validation_phase("preinit", before="init")
    statements.add_validation_fun("preinit", ["*"],
                                  OCLintStages.preinitialisation)

    # Add an openconfig types validation phase where we can
    # get types and then validate them further.
    statements.add_validation_phase("openconfig_type", after="type_2")
    statements.add_validation_fun("openconfig_type", ["*"],
                                  OCLintStages.openconfig_type)

    # pyang manipulates the paths of elements during reference_2, such
    # that this is the only time that we get a chance to work
    statements.add_validation_fun("reference_2", ["*"],
                                  OCLintStages.openconfig_reference)

    # Error type for generic OpenConfig linter bugs - returned
    # when an error is encountered in linter logic.
    error.add_error_code(
        "OC_LINTER_ERROR", ErrorLevel.CRITICAL,
        "Linter error encountered: %s")

    # Enum values must be upper case
    error.add_error_code(
        "OC_ENUM_CASE", ErrorLevel.MAJOR,
        "enum value \"%s\" should be capitalised as \"%s\"")

    # Enum values must be of the form UPPERCASE_WITH_UNDERSCORES
    error.add_error_code(
        "OC_ENUM_UNDERSCORES", ErrorLevel.MAJOR,
        "enum value \"%s\" should be of the form "
        "UPPERCASE_WITH_UNDERSCORES: %s")

    # Identity values should be capitalised
    error.add_error_code(
        "OC_IDENTITY_CASE", ErrorLevel.MAJOR,
        "identity name \"%s\" should be capitalised as \"%s\"")

    # UPPERCASE_WITH_UNDERSCORES required for identity values
    error.add_error_code(
        "OC_IDENTITY_UNDERSCORES", ErrorLevel.MAJOR,
        "identity name \"%s\" should be of the form "
        "UPPERCASE_WITH_UNDERSCORES: \"%s\"")

    # There must be a single config / state container in the path
    error.add_error_code(
        "OC_OPSTATE_CONTAINER_COUNT", ErrorLevel.MAJOR,
        "path \"%s\" should have a single \"config\" or \"state\" component")

    # Leaves should be in a "config" or "state" container
    error.add_error_code(
        "OC_OPSTATE_CONTAINER_NAME", ErrorLevel.MAJOR,
        "element \"%s\" at path \"%s\" should be in a \"config\""
        "or \"state\" container")

    # list keys should be leafrefs to respective value in config / state
    error.add_error_code(
        "OC_OPSTATE_KEY_LEAFREF", ErrorLevel.MAJOR,
        "list key \"%s\" should be type leafref with a reference to"
        " the corresponding leaf in config or state container")

    # leaves in in config / state should have the correct config property
    error.add_error_code(
        "OC_OPSTATE_CONFIG_PROPERTY", ErrorLevel.MAJOR,
        "element \"%s\" is in a \"%s\" container and should have "
        "config value %s")

    # references to nodes in the same module / namespace should use relative
    # paths
    error.add_error_code(
        "OC_RELATIVE_PATH", ErrorLevel.WARNING,
        "\"%s\" path reference \"%s\" is intra-module but uses absolute path")

    # a config leaf does not have a mirrored applied config leaf in the state
    # container
    error.add_error_code(
        "OC_OPSTATE_APPLIED_CONFIG", ErrorLevel.MAJOR,
        "\"%s\" is not mirrored in the state container at %s")

    # a list is within a container that has elements other than the list
    # within it
    error.add_error_code(
        "OC_LIST_SURROUNDING_CONTAINER", ErrorLevel.MAJOR,
        "List %s is within a container (%s) that has other elements "
        "within it: %s")

    # a list that does not have a container above it
    error.add_error_code(
        "OC_LIST_NO_ENCLOSING_CONTAINER", ErrorLevel.MAJOR,
        "List %s does not have a surrounding container")

    # when path compression is performed, the containers surrounding
    # lists are removed, if there are two lists with the same name
    # this results in a name collision.
    error.add_error_code(
        "OC_LIST_DUPLICATE_COMPRESSED_NAME", ErrorLevel.MAJOR,
        "List %s has a duplicate name when the parent container %s" + \
        " is removed.")

    # a module defines data nodes at the top-level
    error.add_error_code(
        "OC_MODULE_DATA_DEFINITIONS", ErrorLevel.MAJOR,
        "Module %s defines data definitions at the top level: %s")

    # a module is missing an openconfig-version statement
    error.add_error_code(
        "OC_MODULE_MISSING_VERSION", ErrorLevel.MAJOR,
        "Module %s is missing an openconfig-version statement")

    # a module uses the "choice" keyword
    error.add_error_code(
        "OC_STYLE_AVOID_CHOICE", ErrorLevel.WARNING,
        "Element %s uses the choice keyword, which should be avoided")

    # a module uses the "presence" keyword
    error.add_error_code(
        "OC_STYLE_AVOID_PRESENCE", ErrorLevel.MINOR,
        "Element %s uses the presence keyword which should be avoided")

    # a module uses the "if-feature" or "feature" keyword
    error.add_error_code(
        "OC_STYLE_AVOID_FEATURES", ErrorLevel.MINOR,
        "Element %s uses feature or if-feature which should be avoided")

    # invalid semantic version argument to openconfig-version
    error.add_error_code(
        "OC_INVALID_SEMVER", ErrorLevel.MAJOR,
        "Semantic version specified (%s) is invalid")

    # missing a revision statement that has a reference of the
    # current semantic version
    error.add_error_code(
        "OC_MISSING_SEMVER_REVISION", ErrorLevel.MAJOR,
        "Revision statement should contain reference substatement "
        " corresponding to semantic version %s")

    # invalid data element naming
    error.add_error_code(
        "OC_DATA_ELEMENT_INVALID_NAME", ErrorLevel.MAJOR,
        "Invalid naming for element %s data elements should "
        " generally be lower-case-with-hypens")

    # the module uses an invalid form of prefix
    error.add_error_code(
        "OC_PREFIX_INVALID", ErrorLevel.MINOR,
        "Prefix %s for module does not match the expected "
        " format - use the form oc-<shortdescription>")

    # the module is missing a standard grouping (e.g., -top)
    error.add_error_code(
        "OC_MISSING_STANDARD_GROUPING", ErrorLevel.WARNING,
        "Module %s is missing a grouping suffixed with %s")

    # the module has a nonstandard grouping name
    error.add_error_code(
        "OC_GROUPING_NAMING_NONSTANDARD", ErrorLevel.WARNING,
        "In container %s, grouping %s does not match standard "
        "naming - suffix with %s?")

    # key statements do not have quoted arguments
    error.add_error_code(
        "OC_KEY_ARGUMENT_UNQUOTED", ErrorLevel.MINOR,
        "All key arguments of a list should be quoted (%s is not)")

    # bad type was used for a leaf or typedef
    error.add_error_code(
        "OC_BAD_TYPE", ErrorLevel.MAJOR,
        "Bad type %s used in leaf or typedef",
    )


class OCLintStages(object):
  """Containing class for OpenConfig linter stages.

    Methods that call the relevant linter functions for a particular
    Pyang validation stage. Each static method of this class is used
    in a validation phase.
  """

  @staticmethod
  def openconfig_override_base_linter(ctx, stmt):
    """Override functions for the base linter.

    Called for particular validation functions that need overrides
    in the context of OpenConfig. This handles cases where there
    are external modules that do not validate according to the
    base rules. It is called as a wrapper for the functions that are
    known to be problematic.

    Args:
      ctx: pyang.Context for the current validation.
      stmt: pyang.Statement matching the validation call.
    """
    if stmt.i_module is not None and \
        stmt.i_module.arg in ["iana-if-type", "ietf-interfaces"]:
      return

    lint.v_chk_recommended_substmt(ctx, stmt)
    lint.v_chk_required_substmt(ctx, stmt)

  @staticmethod
  def preinitialisation(ctx, stmt):
    """Preinitialisation phase validation functions.

    Called on a per-statement basis prior to pyang"s more
    detailed parsing.

    Args:
        ctx: pyang.Context for the current validation.
        stmt: pyang.Statement matching the validation call.
    """
    validmap = {
        u"module": [OCLintFunctions.check_module_rawtext],
        u"submodule": [OCLintFunctions.check_module_rawtext],
    }

    for fn in OCLintStages.map_statement_to_lint_fn(stmt, validmap):
      fn(ctx, stmt)

  @staticmethod
  def openconfig_type(ctx, stmt):
    """OpenConfig types validation functions.

    Called per-statement after pyang's type validation of the
    module - this is used to make stricter rules for type usage.

    Args:
        ctx: pyang.Context for the current validation
        stmt: pyang.Statement matching the validation call.
    """

    validmap = {
        u"*": [
            OCLintFunctions.check_yang_feature_usage,
        ],
        u"LEAVES": [
            OCLintFunctions.check_enumeration_style,
            OCLintFunctions.check_bad_types,
        ],
        u"identity": [
            OCLintFunctions.check_identity_style,
        ],
        u"module": [
            OCLintFunctions.check_versioning,
            OCLintFunctions.check_top_level_data_definitions,
            OCLintFunctions.check_standard_groupings,
        ],
        u"augment": [
            OCLintFunctions.check_relative_paths,
        ],
        u"path": [
            OCLintFunctions.check_relative_paths,
        ],
        u"typedef": [
            OCLintFunctions.check_typedef_style,
        ],
    }

    for fn in OCLintStages.map_statement_to_lint_fn(stmt, validmap):
      fn(ctx, stmt)

  @staticmethod
  def openconfig_reference(ctx, stmt):
    """OpenConfig reference validation phase.

    Validation functions that fit within the reference resolution
    phase of pyang.

    Args:
        ctx: pyang.Context for the current validation
        stmt: pyang.Statement matching the validation call
    """
    validmap = {
        u"LEAVES": [
            OCLintFunctions.check_opstate,
        ],
        u"list": [
            OCLintFunctions.check_list_enclosing_container,
            OCLintFunctions.check_leaf_mirroring,
        ],
        u"container": [
            OCLintFunctions.check_leaf_mirroring,
        ],
    }

    for fn in OCLintStages.map_statement_to_lint_fn(stmt, validmap):
      fn(ctx, stmt)

  @staticmethod
  def map_statement_to_lint_fn(stmt, validation_map):
    """Map for a statement to the lint functions to be run.

    Args:
        stmt: pyang.Statement object for the statement that needs
          the validation functions calculated.
        validation_map: dictionary keyed by statement keyword or a
          list of statement keywords, with values of a list of functions
          that are to be run for that keyword.

    Returns:
      Complete list of functions to be run for the statement.
    """
    functions = []
    defining_module = stmt.pos.ref.split("/")[-1].split(".")[0]
    if (OCLintFunctions.is_openconfig_validatable_module(defining_module) not in
            [ModuleType.OC, ModuleType.OCINFRA]):
      return []

    if u"*" in validation_map:
      functions.extend(validation_map[u"*"])

    if u"LEAVES" in validation_map:
      if stmt.keyword in LEAFNODE_KEYWORDS:
        functions.extend(validation_map[u"LEAVES"])

    if stmt.keyword in validation_map:
      functions.extend(validation_map[stmt.keyword])

    return functions


class OCLintFunctions(object):
  """OpenConfig linter validation functions."""

  @staticmethod
  def check_module_rawtext(ctx, stmt):
    """Perform validation of a module"s raw text.

    Args:
      ctx: The pyang.Context for the current validation.
      stmt: The pyang.Statement for a module that we are parsing
        Function is called once per module to reduce the number of
        iterations through the module.
    """
    try:
      mod_filename = os.path.realpath(stmt.pos.ref).split("/")[-1]
      mod_filename = mod_filename.split(".")[0]
    except IndexError:
      err_add(ctx.errors, stmt.pos, "OC_LINTER_ERROR",
              "Can't determine a module name for %s" % stmt.pos)

    handle = None
    for mod in ctx.repository.get_modules_and_revisions(ctx):
      # stmt.pos.ref gives the reference to the file that this
      # key statement was within
      if mod[0] == mod_filename:
        handle = mod
        break

    if handle is not None:
      try:
        module = ctx.repository.get_module_from_handle(handle[2])
      except (AttributeError, IndexError) as e:
        err_add(ctx.errors, stmt.pos, "OC_LINTER_ERROR",
                "Can't find module %s: %s" % (stmt.pos.ref, e))
        return
    else:
      err_add(ctx.errors, stmt.pos, "OC_LINTER_ERROR",
              "Couldn't open module %s" % stmt.pos.ref)
      return

    key_re = re.compile(r"^([ ]+)?key([ ]+)(?P<arg>[^\"][a-zA-Z0-9\-_]+);$")
    quoted_re = re.compile(r"^\".*\"$")

    ln_count = 0
    for ln in module[2].split("\n"):
      ln_count += 1

      # Remove the newline from the module
      ln = ln.rstrip("\n")
      if key_re.match(ln):
        key_arg = key_re.sub(r"\g<arg>", ln)
        if not quoted_re.match(key_arg):
          # Need to create a fake position object for the
          # key statement because of this pre-initialisation
          # module parse.
          pos = error.Position(stmt.pos.ref)
          pos.line = ln_count

          # Generate an error as the key argument is not
          # quoted.
          err_add(ctx.errors, pos, "OC_KEY_ARGUMENT_UNQUOTED",
                  key_arg)
      ln_count += 1

  @staticmethod
  def is_openconfig_validatable_module(mod):
    """Check whether the module is an OpenConfig module.

    Avoid validating modules that are not OpenConfig.

    Args:
        mod: the text name of the module

    Returns:
      An enumerated ModuleType
    """
    if re.match(r"[a-z0-9]+\-.*", mod.lower()):
      # Avoid parsing IETF and IANA modules which are currently
      # included by OpenConfig, and avoid parsing the extension
      # module itself.
      modname_parts = mod.split("-")
      if modname_parts[0] in [u"ietf", u"iana"]:
        return ModuleType.NONOC
      elif modname_parts[1] == "extensions":
        return ModuleType.OCINFRA
      return ModuleType.OC
    return ModuleType.NONOC

  @staticmethod
  def check_versioning(ctx, stmt):
    """Check that the module has the relevant OC versioning.

    The module needs an openconfig-extensions openconfig-version
    statement, which should match the semantic version format.
    There must also be a revision statement that matches semantic
    version

    Args:
      ctx: pyang.Context for the validation
      stmt: pyang.Statement for the matching module

    """

    # Don't perform this check for modules that are not OpenConfig
    # or are OpenConfig infrastructure (e.g., extensions)
    if (OCLintFunctions.is_openconfig_validatable_module(stmt.arg) in
            [ModuleType.NONOC, ModuleType.OCINFRA]):
      return

    version = None
    for substmt in stmt.substmts:
      # pyang uses a keyword tuple when the element is from
      # an external extension rather than a built-in, check for
      # this before checking the argument. Assumption is made
      # that openconfig-version is unique across all extension
      # modules.
      if (isinstance(substmt.keyword, tuple) and
              substmt.keyword[1] == "openconfig-version"):
        version = substmt

    if version is None:
      err_add(ctx.errors, stmt.pos, "OC_MODULE_MISSING_VERSION",
              stmt.arg)
      return

    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", version.arg):
      err_add(ctx.errors, stmt.pos, "OC_INVALID_SEMVER",
              version.arg)

    # Check that there
    match_revision = False
    for revision_stmt in stmt.search("revision"):
      reference_stmt = revision_stmt.search_one("reference")
      if reference_stmt is not None and reference_stmt.arg == version.arg:
        match_revision = True

    if match_revision is False:
      err_add(ctx.errors, stmt.pos, "OC_MISSING_SEMVER_REVISION",
              version.arg)

  @staticmethod
  def check_top_level_data_definitions(ctx, stmt):
    """Check that the module has no data elements at the root.

    Args:
      ctx: pyang.Context for the validation
      stmt: pyang.Statement for the matching module
    """
    data_definitions = [i.arg for i in stmt.substmts if i.keyword
                        in INSTANTIATED_DATA_KEYWORDS]
    if data_definitions:
      err_add(ctx.errors, stmt.pos, "OC_MODULE_DATA_DEFINITIONS",
              (stmt.arg, ", ".join(data_definitions)))

  @staticmethod
  def check_enumeration_style(ctx, stmt):
    """Check validation rules for OpenConfig enum values.

    Args:
      ctx: pyang.Context for validation
      stmt: pyang.Statement representing a leaf or leaf-list
          containing an enumeration
    """
    elemtype = stmt.search_one("type")
    if elemtype is None or elemtype.arg != "enumeration":
      return

    for enum in elemtype.search("enum"):
      if re.match(r"[a-z]", enum.arg):
        err_add(ctx.errors, stmt.pos, "OC_ENUM_CASE",
                (enum.arg, enum.arg.upper()))
      elif not re.match(r"^[A-Z0-9][A-Z0-9\_\.]+$", enum.arg):
        err_add(ctx.errors, stmt.pos, "OC_ENUM_UNDERSCORES",
                (enum.arg, enum.arg.upper()))

  @staticmethod
  def check_bad_types(ctx, stmt):
    """Check validation rules for bad types that should not
    be used in OpenConfig models.

    Args:
      ctx: pyang.Context for validation
      stmt: pyang.Statement representing a leaf or leaf-list
    """
    elemtype = stmt.search_one("type")
    if elemtype is None or elemtype.arg not in BAD_TYPES:
      return

    err_add(ctx.errors, stmt.pos, "OC_BAD_TYPE",
            (elemtype.arg))

  @staticmethod
  def check_typedef_style(ctx, stmt):
    """Check validation rules for OpenConfig typedef
    statements.

    Args:
      ctx: pyang.Context for validation
      stmt: pyang.Statement representing a typedef.
    """

    elemtype = stmt.search_one("type")
    if elemtype is None:
      return

    # errors are appended to the context, such that we can just call the
    # base checks here.
    OCLintFunctions.check_enumeration_style(ctx, stmt)
    OCLintFunctions.check_bad_types(ctx, stmt)

  @staticmethod
  def check_identity_style(ctx, stmt):
    """Check validation rules for OpenConfig identity leaves.

    Args:
      ctx: pyang.Context for validation
      stmt: pyang.Statemnet representing a leaf or leaf-list
          containing an identity
    """
    if stmt.keyword != "identity":
      return

    if re.match(r"^[a-z]", stmt.arg):
      err_add(ctx.errors, stmt.pos, "OC_IDENTITY_CASE",
              (stmt.arg, stmt.arg.upper()))
    elif not re.match(r"^[A-Z][A-Z0-9\_\.]+$", stmt.arg):
      err_add(ctx.errors, stmt.pos, "OC_IDENTITY_UNDERSCORES",
              (stmt.arg, stmt.arg.upper()))

  @staticmethod
  def check_opstate(ctx, stmt):
    """Check operational state validation rules.

    Args:
      ctx: pyang.Context for validation
      stmt: pyang.Statement for a leaf or leaf-list
    """
    pathstr = statements.mk_path_str(stmt)

    # leaves that are list keys are exempt from this check.  YANG
    # requires them at the top level of the list, i.e., not allowed
    # in a descendent container
    is_key = False
    if stmt.parent.keyword == "list" and stmt.keyword == "leaf":
      key_stmt = stmt.parent.search_one("key")
      if key_stmt is not None:
        if " " in key_stmt.arg:
          key_parts = [i for i in key_stmt.arg.split(" ")]
        else:
          key_parts = [key_stmt.arg]

        if stmt.arg in key_parts:
          is_key = True

    if is_key:
      keytype = stmt.search_one("type")
      if keytype.arg != "leafref":
        err_add(ctx.errors, stmt.pos, "OC_OPSTATE_KEY_LEAFREF",
                stmt.arg)
      return

    path_elements = yangpath.split_paths(pathstr)
    # count number of 'config' and 'state' elements in the path
    confignum = path_elements.count("config")
    statenum = path_elements.count("state")
    if confignum != 1 and statenum != 1:
      err_add(ctx.errors, stmt.pos, "OC_OPSTATE_CONTAINER_COUNT",
              (pathstr))

    # for elements in a config or state container, make sure they have the
    # correct config property
    if stmt.parent.keyword == "container":
      if stmt.parent.arg == "config":
        if stmt.i_config is False:
          err_add(ctx.errors, stmt.pos, "OC_OPSTATE_CONFIG_PROPERTY",
                  (stmt.arg, "config", "true"))
      elif stmt.parent.arg == "state":
        if stmt.i_config is True:
          err_add(ctx.errors, stmt.parent.pos, "OC_OPSTATE_CONFIG_PROPERTY",
                  (stmt.arg, "state", "false"))
      else:
        valid_enclosing_state = False

        if stmt.i_config is False:
          # Allow nested containers within a state container
          path_elements = yangpath.split_paths(pathstr)
          if u"state" in path_elements:
            valid_enclosing_state = True

        if valid_enclosing_state is False:
          err_add(ctx.errors, stmt.pos, "OC_OPSTATE_CONTAINER_NAME",
                  (stmt.arg, pathstr))

  @staticmethod
  def check_list_enclosing_container(ctx, stmt):
    """Check that a list has an enclosing container and that its
    name is not duplicated when path compression is performed.

    Args:
      ctx: pyang.Context for the validation
      stmt: pyang.Statement for the list
    """

    parent_substmts = [i.arg for i in stmt.parent.i_children
                       if i.keyword in INSTANTIATED_DATA_KEYWORDS]

    if stmt.parent.keyword != "container":
      err_add(ctx.errors, stmt.parent.pos,
              "OC_LIST_NO_ENCLOSING_CONTAINER", stmt.arg)

    grandparent = stmt.parent.parent
    for ch in grandparent.i_children:
      if ch.keyword == "container" and ch.arg != stmt.parent.arg:
        if len(ch.i_children) == 1 and ch.i_children[0].arg == stmt.arg \
            and ch.i_children[0].keyword == "list":
          err_add(ctx.errors, stmt.parent.pos,
                  "OC_LIST_DUPLICATE_COMPRESSED_NAME",
                  (stmt.arg, stmt.parent.arg))

    if parent_substmts != [stmt.arg]:
      remaining_parent_substmts = [i.arg for i in stmt.parent.i_children
                                   if i.arg != stmt.arg and i.keyword
                                   in INSTANTIATED_DATA_KEYWORDS]
      err_add(ctx.errors, stmt.parent.pos,
              "OC_LIST_SURROUNDING_CONTAINER",
              (stmt.arg, stmt.parent.arg,
               ", ".join(remaining_parent_substmts)))

  @staticmethod
  def check_leaf_mirroring(ctx, stmt):
    """Check applied configuration mirrors intended configuration.

    Check that each leaf in config has a corresponding leaf in state.

    Args:
      ctx: pyang.Context for the validation
      stmt: pyang.Statement for the parent container or list.
    """

    # Skip the check if the container is not a parent of other containers
    if stmt.search_one("container") is None:
      return

    containers = stmt.search("container")
    # Only perform this check if this is a container that has both a config
    # and state container
    c_config, c_state = None, None
    for c in containers:
      if c.arg == "config":
        c_config = c
      elif c.arg == "state":
        c_state = c

    if None in [c_config, c_state]:
      return

    config_elem_names = [i.arg for i in c_config.i_children
                         if i.arg != "config" and
                         i.keyword in INSTANTIATED_DATA_KEYWORDS]
    state_elem_names = [i.arg for i in c_state.i_children
                        if i.arg != "state" and
                        i.keyword in INSTANTIATED_DATA_KEYWORDS]

    for elem in config_elem_names:
      if elem not in state_elem_names:
        err_add(ctx.errors, stmt.parent.pos, "OC_OPSTATE_APPLIED_CONFIG",
                (elem, statements.mk_path_str(stmt, False)))

  @staticmethod
  def check_yang_feature_usage(ctx, stmt):
    """Check whether undesirable YANG features are used.

    Args:
      ctx: pyang.Context for the validation
      stmt: pyang.Statement object for the statement the validation function
          is called for.
    """
    if stmt.keyword == "choice":
      err_add(ctx.errors, stmt.pos, "OC_STYLE_AVOID_CHOICE",
              (stmt.arg))
    elif stmt.keyword == "presence":
      err_add(ctx.errors, stmt.pos, "OC_STYLE_AVOID_PRESENCE",
              (stmt.parent.arg))
    elif stmt.keyword == "feature":
      err_add(ctx.errors, stmt.pos, "OC_STYLE_AVOID_FEATURES",
              (stmt.arg))
    elif stmt.keyword == "if-feature":
      err_add(ctx.errors, stmt.parent.pos, "OC_STYLE_AVOID_FEATURES",
              (stmt.parent.arg))

  @staticmethod
  def check_relative_paths(ctx, stmt):
    """Check whether relative paths are used within a module.

    Args:
      ctx: pyang.Context for the validation
      stmt: pyang.Statement object for the statement the validation function
      is called for.
    """
    path = stmt.arg
    if path[0] == "/":
      abspath = True
    else:
      abspath = False

    components = yangpath.split_paths(path)
    # consider the namespace in the first component
    # assumes that if the namespace matches the module namespace, then
    # relative path should be used (intra-module)
    if ":" in components[0]:
      namespace = components[0].split(":")[0]
    else:
      namespace = stmt.i_module.i_prefix

    mod_prefix = stmt.i_module.i_prefix

    if namespace == mod_prefix and abspath:
      # Don't throw a warning if the absolute path is within the
      # current module if the statement is within a typedef. This
      # allows types to be defined that refer to an element of a
      # module without errors being generated.
      is_typedef = False
      if stmt.parent is not None and stmt.parent.parent is not None:
        if stmt.parent.parent.keyword == "typedef":
          is_typedef = True

      if not is_typedef:
        err_add(ctx.errors, stmt.pos, "OC_RELATIVE_PATH",
                (stmt.keyword, stmt.arg))

  @staticmethod
  def check_standard_groupings(ctx, stmt):
    """Check whether there are missing standard groupings in the model.

    Args:
        ctx:  pyang.Context for the validation
        stmt: pyang.Statement for the statement that has been called on.
    """

    # Don't perform this check for modules that are not OpenConfig
    # or are OpenConfig infrastructure (e.g., extensions)
    if (OCLintFunctions.is_openconfig_validatable_module(stmt.arg) in
            [ModuleType.NONOC, ModuleType.OCINFRA]):
      return

    found = False
    for grouping in stmt.search("grouping"):
      if re.match(r".*\-top$", grouping.arg):
        found = True

    if not found:
      err_add(ctx.errors, stmt.pos, "OC_MISSING_STANDARD_GROUPING",
              (stmt.arg, "-top"))
