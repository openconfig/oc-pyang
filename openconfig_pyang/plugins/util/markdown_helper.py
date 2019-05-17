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


Helper class to generate Markdown syntax

"""


class MarkdownHelper:
    def h1(self, text):
        return "# " + text + " #"

    def h2(self, text):
        return "#" * 2 + " " + text + " " + "#" * 2

    def h3(self, text):
        return "#" * 3 + " " + text + " " + "#" * 3

    def h4(self, text):
        return "#" * 4 + " " + text + " " + "#" * 4

    def h5(self, text):
        return "#" * 5 + " " + text + " " + "#" * 5

    def h6(self, text):
        return "#" * 6 + " " + text + " " + "#" * 6

    def h(self, size, text):
        if size < 1:
            return self.h1(text)
        elif size > 6:
            return self.h6(text)
        else:
            return getattr(self, "h" + str(size))(text)

    def ul(self, list):
        s = ""
        for item in list:
            # strips all newlines before adding a single one -- effectively
            # prevents the markdown that causes list items to be wrapped in
            # paragraph tags
            s += "* " + str(item).strip("\n") + "\n"

        return s

    def ol(self, list):
        s = ""
        n = 1
        for item in list:
            # strips all newlines before adding a single one -- effectively
            # prevents the markdown that causes list items to be wrapped in
            # paragraph tags
            s += str(n) + ". " + str(item).strip("\n") + "\n"
            n += 1

        return s

    def hr(self):
        return "------------\n"

    def i(self, text):
        # add emphasis to supplied text
        return "*" + text + "*"

    def b(self, text):
        # add double emphasis (i.e., bold)
        return "**" + text + "**"

    def code(self, text):
        # format as inline code
        return "`" + text + "`"
