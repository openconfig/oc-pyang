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


Defines the API for a documentation emitter for YANG modules

"""

from collections import OrderedDict

class DocEmitter:

  def __init__(self):
    self.path_only = []
    # moduledocs is an ordered, nested map that contains an entry
    # for each part of a module's documentation, keyed
    # by the module name -- within each nested map, keys are
    # "module", "typedefs", "identities", "data", and values
    # are strings containing the emitted documentation.
    # Specific emitters may add additional elements as
    # needed (e.g., menu content, navbars, etc.)
    self.moduledocs = OrderedDict()

  def genModuleDoc(self, mod, ctx):
    """Given a ModuleDoc object, generates markup for the
    top-level module documentation, including typedefs and
    identities"""
    pass

  def genStatementDoc(self, statement, ctx):
    """Generates the documentation for the supplied StatementDoc object
    """
    pass

  def emitDocs(self, ctx, section=None):
    """Returns the documentation for the full module or, optionally,
    the specified section of a module.  If specified, section should be
    one of: "module", "typedefs", "identities", or "data" """
    pass