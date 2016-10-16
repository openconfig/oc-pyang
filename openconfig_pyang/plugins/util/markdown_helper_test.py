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

Test data for markdown_helper

"""

import markdown_helper


def main():

  a_list = ['red', 'green', 'blue', 'orange']
  text = 'a line of text'

  md = markdown_gen.MarkdownGen()
  print md.h1(text)
  print md.h2(text)
  print md.h3(text)
  print md.h4(text)
  print md.h5(text)
  print md.h6(text)

  print md.h(8,text)

  print md.hr()

  print md.ol(a_list)

  print md.ul(a_list)

  print md.hr()

  print md.i(text)
  print md.b(text)
  print md.code(text)



if __name__ == '__main__':
  main( )
