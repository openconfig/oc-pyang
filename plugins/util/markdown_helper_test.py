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
