import html_helper


def main():

  a_list = ['red', 'green', 'blue', 'orange']
  text = 'a line of text'
  attrs = {"class":"my-css-class", "id":"element-id"}
  tag = "span"
  label = "label:"

  paragraph = "Lorem ipsum dolor sit amet, consectetur adipiscing\
  elit. Nunc maximus, dui non sollicitudin sollicitudin, leo nibh\
  luctus orci, varius maximus lacus nulla eget nibh. Nulla faucibus\
  purus nulla, eu molestie massa cursus vitae. Vestibulum metus purus,\
  tempus sed risus ac, lobortis efficitur lorem."

  ht = html_helper.HTMLHelper()
  print ht.h1(text)
  print ht.h1(text, attrs)
  print "\n"
  print ht.h2(text)
  print ht.h2(text, attrs)
  print "\n"
  print ht.h3(text)
  print ht.h3(text, attrs)
  print "\n"
  print ht.h4(text)
  print ht.h4(text, attrs)
  print "\n"
  print ht.h5(text)
  print ht.h5(text, attrs)
  print "\n"
  print ht.h6(text)
  print ht.h6(text, attrs)

  print ht.h1(text, attrs, 5, True)
  print ht.h1(text, attrs, 2, False)

  print ht.h(8,text,attrs)
  print ht.h(-1,text,attrs)

  print ht.hr()

  print ht.add_tag (tag, text, attrs)
  print ht.add_tag (tag, text)
  print "\n"

  print ht.para(paragraph, attrs)
  print "\n"
  print ht.para(ht.add_tag(tag,label) + paragraph)
  print "\n"

  print ht.open_tag("div")
  print ht.para(paragraph)
  print ht.close_tag()

  # print md.ol(a_list)

  # print md.ul(a_list)

  # print md.hr()

  # print md.i(text)
  # print md.b(text)
  # print md.code(text)



if __name__ == '__main__':
  main( )
