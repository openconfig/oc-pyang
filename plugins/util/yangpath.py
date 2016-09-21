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


Utilities for manipulating YANG paths

"""

import re

def split_paths(path):
  """ return a list of path elements """

  components = path.split('/')
  return [c for c in components if c]

def strip_namespace(path):
  """Removes namespace prefixes from elements of the supplied path"""
  re_ns = re.compile (r'^.+:')
  #pathstr = re_ns.sub('/', pathstr, 0)
  path_components = [re_ns.sub('',comp) for comp in path.split('/')]
  pathstr = '/'.join(path_components)
  return pathstr

def remove_last(path):
  """Removes the last path element and returns both parts.  Note the
  last '/' is not returned in either part"""
  components = path.split('/')
  last = components.pop()
  prefix = '/'.join(components)
  return (prefix, last)