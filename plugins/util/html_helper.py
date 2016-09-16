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


Simple helper class to generate HTML elements for YANG documentation.
This module implements a small subset of HTML tags.

"""

import re

class HTMLHelper:
  """Implements some simple HTML element generation to support
  documentation.  Most functions take text and a map of attributes
  to add."""

  last_tag = None

  def h1(self, text, attrs=None, indent=0, newline=False):
    return self.h(1, text, attrs, indent, newline)

  def h2(self, text, attrs=None, indent=0, newline=False):
    return self.h(2, text, attrs, indent, newline)

  def h3(self, text, attrs=None, indent=0, newline=False):
    return self.h(3, text, attrs, indent, newline)

  def h4(self, text, attrs=None, indent=0, newline=False):
    return self.h(4, text, attrs, indent, newline)

  def h5(self, text, attrs=None, indent=0, newline=False):
    return self.h(5, text, attrs, indent, newline)

  def h6(self, text, attrs=None, indent=0, newline=False):
    return self.h(6, text, attrs, indent, newline)

  def h(self, size, text, attrs=None, indent=0, newline=False):
    if size < 1:
      size = 1
    elif size > 6:
      size = 6
    if attrs:
      return "%s<h%d %s>%s</h%d>%s" % (" "*indent, size, get_attr_str(attrs), text, size, ("\n" if newline is True else ""))
    else:
      return "%s<h%d>%s</h%d>%s" % (" "*indent, size, text, size, ("\n" if newline is True else ""))

    if size < 1:
      return self.h1(text)
    elif size > 6:
      return self.h6(text)
    else:
      return getattr(self, 'h'+str(size))(text)

  def add_tag(self, tag, text, attrs=None, indent=0, newline=False):
    """General purpose function to add an HTML element
    tag to the given text with the optional attributes. tag
    parameter should be just the tag name without any
    brackets, etc."""
    if attrs:
      return "%s<%s %s>%s</%s>%s" % (" "*indent, tag, get_attr_str(attrs), text, tag, ("\n" if newline is True else ""))
    else:
      return "%s<%s>%s</%s>%s" % (" "*indent,tag, text, tag,("\n" if newline is True else ""))

  def open_tag(self,tag,attrs=None, indent=0, newline=False):
    self.last_tag = tag
    if attrs:
      return "%s<%s %s>%s" % (" "*indent, tag, get_attr_str(attrs),("\n" if newline is True else ""))
    else:
      return "%s<%s>%s" % (" "*indent,tag,("\n" if newline is True else ""))

  def close_tag(self,opttag=None, indent=0, newline=False):
    if opttag is None:
      tag = self.last_tag
    else:
      tag = opttag
    self.last_tag = None
    return "%s</%s>%s" % (" "*indent,tag,("\n" if newline is True else ""))

  def para(self, text, attrs=None, indent=0, newline=False):
    if attrs:
      return "%s<p %s>%s</p>%s" % (" "*indent, get_attr_str(attrs), text, ("\n" if newline is True else ""))
    else:
      return "%s<p>%s</p>%s" % (" "*indent,text,("\n" if newline is True else ""))


  def ul(self, list, attrs=None, indent=0, newline=False):
    if attrs:
      s = "%s<ul %s>%s" % (" "*indent, get_attr_str(attrs), ("\n" if newline is True else ""))
    else:
      s = "%s<ul>%s" % (" "*indent, ("\n" if newline is True else ""))
    for item in list:
      # strips all newlines before adding a single one -- effectively
      # prevents the markdown that causes list items to be wrapped in
      # paragraph tags
      s += "%s<li>%s</li>\n" % (" "*indent, item)

    s += "%s</ul>%s" % (" "*indent, ("\n" if newline is True else ""))

    return s

  def ol(self, list):
    s = ''
    n = 1
    for item in list:
      # strips all newlines before adding a single one -- effectively
      # prevents the markdown that causes list items to be wrapped in
      # paragraph tags
      s += str(n) + ". " + str(item).strip('\n') + "\n"
      n += 1

    return s

  def hr(self, indent=0, newline=False):
    return "%s<hr />%s" % (" "*indent, ("\n" if newline is True else ""))

  def br(self, indent=0, newline=False):
    return "%s<br />%s" % (" "*indent, ("\n" if newline is True else ""))

  def i(self, text):
    # add emphasis to supplied text
    return "*" + text + "*"

  def b(self, text):
    # add double emphasis (i.e., bold)
    return "**" + text + "**"

  def code(self, text, attrs=None, indent=0, newline=False):
    # format as inline code
    if attrs:
      return "%s<pre %s>%s</pre>%s" % (" "*indent, get_attr_str(attrs), text, ("\n" if newline is True else ""))
    else:
      return "%s<pre>%s</pre>%s" % (" "*indent,text,("\n" if newline is True else ""))

  def gen_html_id(self, text):
    """Given a string, transforms into a suitable html id"""
    id = text.lstrip('_/- ')
    id = re.sub(r'[ /]', r'-', text)
    return (id.lower().strip())

def get_attr_str(attrs):
  elem_attrs = []
  for attr_val in attrs.items():
    elem_attrs.append("%s=\"%s\"" % attr_val)
  return " ".join(elem_attrs)
