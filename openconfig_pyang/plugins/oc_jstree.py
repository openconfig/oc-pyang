"""
Copyright 2017 Google, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Modified version of the original jstree plugin distributed with pyang.

Original copyright and license:

Copyright (c) 2007-2013, Martin Bjorklund, mbj@tail-f.com

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

JS-Tree output plugin
Generates a html/javascript page that presents a tree-navigator
to the YANG module(s).
"""

import optparse
import sys
import re

from pyang import plugin
from pyang import statements


def pyang_plugin_init():
    plugin.register_plugin(JSTreePlugin())


class JSTreePlugin(plugin.PyangPlugin):
    def add_output_format(self, fmts):
        self.multiple_modules = True
        fmts["oc-jstree"] = self

    def add_opts(self, optparser):
        optlist = [
            optparse.make_option(
                "--oc-jstree-no-path",
                dest="jstree_no_path",
                action="store_true",
                help="""Do not include paths to make
                                       page less wide""",
            ),
            optparse.make_option(
                "--oc-jstree-strip",
                dest="strip_namespace",
                action="store_true",
                help="""Strip namespace prefixes from
                                path components""",
            ),
        ]

        g = optparser.add_option_group("OpenConfig JSTree output specific options")
        g.add_options(optlist)

    def setup_fmt(self, ctx):
        ctx.implicit_errors = False

    def emit(self, ctx, modules, fd):
        emit_header(modules, fd, ctx)
        emit_css(fd, ctx)
        emit_js(fd, ctx)
        emit_bodystart(modules, fd, ctx)
        emit_tree(modules, fd, ctx)
        emit_footer(fd, ctx)


def emit_css(fd, ctx):
    fd.write(
        """
<style type="text/css" media="all">

body, h1, h2, h3, h4, h5, h6, p, td, table td, input, select {
        font-family: Verdana, Helvetica, Arial, sans-serif;
        font-size: 10pt;
}

body, ol, li, h2 {padding:0; margin: 0;}

ol#root  {padding-left: 5px; margin-top: 2px; margin-bottom: 1px;
          list-style: none;}

#root ol {padding-left: 5px; margin-top: 2px; margin-bottom: 1px;
          list-style: none;}

#root li {margin-bottom: 1px; padding-left: 5px;  margin-top: 2px;
          font-size: x-small;}

.panel   {border-bottom: 1px solid #999; margin-bottom: 2px; margin-top: 2px;
          background: #eee;}

#root ul {margin-bottom: 1px; margin-top: 2px; list-style-position: inside;}

#root a {text-decoration: none;}

.folder {
   """
        + get_folder_css()
        + """
}

.doc {
   """
        + get_doc_css()
        + """
}

.leaf {
   """
        + get_leaf_css()
        + """
}

.leaf-list {
   """
        + get_leaf_list_css()
        + """
}

.action {
   """
        + get_action_css()
        + """
}

.tier1  {margin-left: 0;     }

.level1 {padding-left: 0;    }
.level2 {padding-left: 1em;  }
.level3 {padding-left: 2em;  }
.level4 {padding-left: 3em;  }
</style>
"""
    )


def emit_js(fd, ctx):
    fd.write(
        """
<script language="javascript1.2">
function toggleRows(elm) {
 var rows = document.getElementsByTagName("TR");
 elm.style.backgroundImage = """
        + '"'
        + get_leaf_img()
        + '"'
        + """;
 var newDisplay = "none";
 var thisID = elm.parentNode.parentNode.parentNode.id + "-";
 // Are we expanding or contracting? If the first child is hidden, we expand
  for (var i = 0; i < rows.length; i++) {
   var r = rows[i];
   if (matchStart(r.id, thisID, true)) {
    if (r.style.display == "none") {
     if (document.all) newDisplay = "block"; //IE4+ specific code
     else newDisplay = "table-row"; //Netscape and Mozilla
     elm.style.backgroundImage = """
        + '"'
        + get_folder_open_img()
        + '"'
        + """;
    }
    break;
   }
 }

 // When expanding, only expand one level.  Collapse all desendants.
 var matchDirectChildrenOnly = (newDisplay != "none");

 for (var j = 0; j < rows.length; j++) {
   var s = rows[j];
   if (matchStart(s.id, thisID, matchDirectChildrenOnly)) {
     s.style.display = newDisplay;
     var cell = s.getElementsByTagName("TD")[0];
     var tier = cell.getElementsByTagName("DIV")[0];
     var folder = tier.getElementsByTagName("A")[0];
     if (folder.getAttribute("onclick") != null) {
     folder.style.backgroundImage = """
        + '"'
        + get_folder_closed_img()
        + '"'
        + """;
     }
   }
 }
}

function matchStart(target, pattern, matchDirectChildrenOnly) {
 var pos = target.indexOf(pattern);
 if (pos != 0)
    return false;
 if (!matchDirectChildrenOnly)
    return true;
 if (target.slice(pos + pattern.length, target.length).indexOf("-") >= 0)
    return false;
 return true;
}

function collapseAllRows() {
 var rows = document.getElementsByTagName("TR");
 for (var i = 0; i < rows.length; i++) {
   var r = rows[i];
   if (r.id.indexOf("-") >= 0) {
     r.style.display = "none";
   }
 }
}

function expandAllRows() {
  var rows = document.getElementsByTagName("TR");
  for (var i = 0; i < rows.length; i ++) {
    var r = rows[i];
    if (r.id.indexOf("-") >= 0) {
      r.style.display = "table-row";
    }
  }
}
</script>
"""
    )


def emit_header(modules, fd, ctx):
    title = ""
    for m in modules:
        title = title + " " + m.arg
    fd.write("<head><title>%s \n</title>" % title)


def emit_footer(fd, ctx):
    fd.write(
        """
</table>
</div>
</body>
</html>

"""
    )


levelcnt = [0] * 100


def emit_bodystart(modules, fd, ctx):
    fd.write(
        """
<body onload="collapseAllRows();">
<div>
  <a href="http://www.openconfig.net">
   <img style="display: inline-block;vertical-align: middle;" src="""
        + get_openconfig_logo()
        + """ />
  </a>
<span style="float: right;">generated by <a href="https://github.com/mbj4668/pyang">pyang</a></span>
</div>
<div class="app">
<div style="border: dashed 1px #000;">
"""
    )
    for module in modules:
        bstr = ""
        b = module.search_one("belongs-to")
        if b is not None:
            bstr = " (belongs-to %s)" % b.arg

        nsstr = ""
        ns = module.search_one("namespace")
        if ns is not None:
            nsstr = ns.arg
        pr = module.search_one("prefix")

        prstr = ""
        if pr is not None:
            prstr = pr.arg

        if module.keyword == "module":
            fd.write(
                """<h1> %s: <font color=blue>%s%s</font>, Namespace:
                    <font color=blue>%s</font>, Prefix:
                    <font color=blue>%s</font></h1> \n"""
                % (module.keyword.capitalize(), module.arg, bstr, nsstr, prstr)
            )
        else:
            fd.write(
                "<h1> %s: <font color=blue>%s%s</font></h1> \n"
                % (module.keyword.capitalize(), module.arg, bstr)
            )

    fd.write(
        """
 <table width="100%">

 <tr>
  <!-- specifing one or more widths keeps columns
       constant despite changes in visible content -->
  <th align=left>
     Element
     <a href='#' onclick='expandAllRows();'>[+]Expand all</a>
     <a href='#' onclick='collapseAllRows();'>[-]Collapse all</a>
  </th>
  <th align=left>Schema</th>
  <th align=left>Type</th>
  <th align=left>Flags</th>
  <th align=left>Opts</th>
  <th align=left>Status</th>
"""
    )
    if not ctx.opts.jstree_no_path:
        fd.write(
            """
  <th align=left>Path</th>
</tr>
"""
        )
    else:
        fd.write(
            """
</tr>
"""
        )


def emit_tree(modules, fd, ctx):
    global levelcnt
    for module in modules:
        bstr = ""
        b = module.search_one("belongs-to")
        if b is not None:
            bstr = " (belongs-to %s)" % b.arg
        ns = module.search_one("namespace")
        if ns is not None:
            nsstr = ns.arg
        pr = module.search_one("prefix")
        if pr is not None:
            prstr = pr.arg
        else:
            prstr = ""

        temp_mod_arg = module.arg
        # html plugin specific changes
        if hasattr(ctx, "html_plugin_user"):
            from pyang.plugins.html import force_link

            temp_mod_arg = force_link(ctx, module, module)

        levelcnt[1] += 1
        fd.write(
            """<tr id="%s" class="a">
                     <td id="p1">
                        <div id="p2" class="tier1">
                           <a href="#" id="p3"
                              onclick="toggleRows(this);return false;"
                              class="folder">&nbsp;
                           </a>
                           <font color=blue>%s</font>
                        </div>
                     </td> \n"""
            % (levelcnt[1], temp_mod_arg)
        )
        fd.write(
            """<td>%s</td><td></td><td></td><td></td><td>
                    </td></tr>\n"""
            % module.keyword
        )
        # fd.write("<td>module</td><td></td><td></td><td></td><td></td></tr>\n")

        chs = [
            ch
            for ch in module.i_children
            if ch.keyword in statements.data_definition_keywords
        ]
        print_children(chs, module, fd, " ", ctx, 2)

        rpcs = module.search("rpc")
        levelcnt[1] += 1
        if len(rpcs) > 0:
            fd.write(
                """<tr id="%s" class="a">
                         <td nowrap id="p1000">
                            <div id="p2000" class="tier1">
                               <a href="#" id="p3000"
                                  onclick="toggleRows(this);
                                  return false;" class="folder">&nbsp;
                               </a>
                               %s:rpcs
                            </div>
                         </td> \n"""
                % (levelcnt[1], prstr)
            )
            fd.write("<td></td><td></td><td></td><td></td><td></td></tr>\n")
            print_children(rpcs, module, fd, " ", ctx, 2)

        notifs = module.search("notification")
        levelcnt[1] += 1
        if len(notifs) > 0:
            fd.write(
                """<tr id="%s" class="a">
                        <td nowrapid="p4000">
                           <div id="p5000" class="tier1">
                              <a href="#" id="p6000"
                                 onclick="toggleRows(this);return false;"
                                 class="folder">&nbsp;
                              </a>%s:notifs
                           </div>
                        </td> \n"""
                % (levelcnt[1], prstr)
            )
            fd.write("<td></td><td></td><td></td><td></td><td></td></tr>\n")
            print_children(notifs, module, fd, " ", ctx, 2)


def print_children(i_children, module, fd, prefix, ctx, level=0):
    for ch in i_children:
        print_node(ch, module, fd, prefix, ctx, level)


def print_node(s, module, fd, prefix, ctx, level=0):

    global levelcnt
    fontstarttag = ""
    fontendtag = ""
    status = get_status_str(s)
    nodetype = ""
    options = ""
    folder = False
    if s.i_module.i_modulename == module.i_modulename:
        name = s.arg
    else:
        name = s.i_module.i_prefix + ":" + s.arg

    pr = module.search_one("prefix")
    if pr is not None:
        prstr = pr.arg
    else:
        prstr = ""

    descr = s.search_one("description")
    descrstring = "No description"
    if descr is not None:
        descrstring = descr.arg
    flags = get_flags_str(s)
    if s.keyword == "list":
        folder = True
    elif s.keyword == "container":
        folder = True
        p = s.search_one("presence")
        if p is not None:
            pr_str = p.arg
            options = '<abbr title="' + pr_str + '">Presence</abbr>'
    elif s.keyword == "choice":
        folder = True
        m = s.search_one("mandatory")
        if m is None or m.arg == "false":
            name = "(" + s.arg + ")"
            options = "Choice"
        else:
            name = "(" + s.arg + ")"
    elif s.keyword == "case":
        folder = True
        # fd.write(':(' + s.arg + ')')
        name = ":(" + s.arg + ")"
    elif s.keyword == "input":
        folder = True
    elif s.keyword == "output":
        folder = True
    elif s.keyword == "rpc":
        folder = True
    elif s.keyword == "notification":
        folder = True
    else:
        if s.keyword == "leaf-list":
            options = "*"
        elif s.keyword == "leaf" and not hasattr(s, "i_is_key"):
            m = s.search_one("mandatory")
            if m is None or m.arg == "false":
                options = "?"
        nodetype = get_typename(s)

    if s.keyword == "list" and s.search_one("key") is not None:
        name += "[" + s.search_one("key").arg + "]"

    descr = s.search_one("description")
    if descr is not None:
        descrstring = "".join([x for x in descr.arg if ord(x) < 128])
    else:
        descrstring = "No description"
    levelcnt[level] += 1
    idstring = str(levelcnt[1])

    for i in range(2, level + 1):
        idstring += "-" + str(levelcnt[i])

    pathstr = statements.mk_path_str(s, True)
    if not ctx.opts.jstree_no_path:
        if ctx.opts.strip_namespace:
            re_ns = re.compile(r"^.+:")
            path_components = [re_ns.sub("", comp) for comp in pathstr.split("/")]
            pathstr = "/".join(path_components)
    else:
        # append the path to the description popup
        descrstring = descrstring + "\n\npath: " + pathstr
        pathstr = ""

    if "?" in options:
        fontstarttag = "<em>"
        fontendtag = "</em>"
    keyword = s.keyword

    if folder:
        # html plugin specific changes
        if hasattr(ctx, "html_plugin_user"):
            from pyang.plugins.html import force_link

            name = force_link(ctx, s, module, name)
        fd.write(
            """<tr id="%s" class="a">
                       <td nowrap id="p4000">
                          <div id="p5000" style="margin-left:%sem;">
                             <a href="#" id="p6000"
                                onclick="toggleRows(this);return false"
                                class="folder">&nbsp;
                             </a>
                             <abbr title="%s">%s</abbr>
                          </div>
                       </td> \n"""
            % (idstring, (level * 1.5 - 1.5), descrstring, name)
        )
        fd.write(
            """<td nowrap>%s</td>
                    <td nowrap>%s</td>
                    <td nowrap>%s</td>
                    <td>%s</td>
                    <td>%s</td>
                    <td nowrap>%s</td>
                    </tr> \n"""
            % (s.keyword, nodetype, flags, options, status, pathstr)
        )
    else:
        if s.keyword in ["action", ("tailf-common", "action")]:
            classstring = "action"
            typeinfo = action_params(s)
            typename = "parameters"
            keyword = "action"
        elif s.keyword == "rpc" or s.keyword == "notification":
            classstring = "folder"
            typeinfo = action_params(s)
            typename = "parameters"
        else:
            classstring = s.keyword
            typeinfo = typestring(s)
            typename = nodetype
        fd.write(
            """<tr id="%s" class="a">
                       <td nowrap>
                          <div id=9999 style="margin-left: %sem;">
                             <a class="%s">&nbsp;</a>
                             <abbr title="%s"> %s %s %s</abbr>
                          </div>
                       </td>
                       <td>%s</td>
                       <td nowrap><abbr title="%s">%s</abbr></td>
                       <td nowrap>%s</td>
                       <td>%s</td>
                       <td>%s</td>
                       <td nowrap>%s</td</tr> \n"""
            % (
                idstring,
                (level * 1.5 - 1.5),
                classstring,
                descrstring,
                fontstarttag,
                name,
                fontendtag,
                keyword,
                typeinfo,
                typename,
                flags,
                options,
                status,
                pathstr,
            )
        )

    if hasattr(s, "i_children"):
        level += 1
        if s.keyword in ["choice", "case"]:
            print_children(s.i_children, module, fd, prefix, ctx, level)
        else:
            print_children(s.i_children, module, fd, prefix, ctx, level)


def get_status_str(s):
    status = s.search_one("status")
    if status is None or status.arg == "current":
        return "current"
    else:
        return status


def get_flags_str(s):
    if s.keyword == "rpc":
        return ""
    elif s.keyword == "notification":
        return ""
    elif s.i_config == True:
        return "config"
    else:
        return "no config"


def get_typename(s):
    t = s.search_one("type")
    if t is not None:
        return t.arg
    else:
        return ""


def typestring(node):
    def get_nontypedefstring(node):
        s = ""
        found = False
        t = node.search_one("type")
        if t is not None:
            s = t.arg + "\n"
            if t.arg == "enumeration":
                found = True
                s = s + " : {"
                for enums in t.substmts:
                    s = s + enums.arg + ","
                s = s + "}"
            elif t.arg == "leafref":
                found = True
                s = s + " : "
                p = t.search_one("path")
                if p is not None:
                    s = s + p.arg

            elif t.arg == "identityref":
                found = True
                b = t.search_one("base")
                if b is not None:
                    s = s + " {" + b.arg + "}"

            elif t.arg == "union":
                found = True
                uniontypes = t.search("type")
                s = s + "{" + uniontypes[0].arg
                for uniontype in uniontypes[1:]:
                    s = s + ", " + uniontype.arg
                s = s + "}"

            typerange = t.search_one("range")
            if typerange is not None:
                found = True
                s = s + " [" + typerange.arg + "]"
            length = t.search_one("length")
            if length is not None:
                found = True
                s = s + " {length = " + length.arg + "}"

            pattern = t.search_one("pattern")
            if pattern is not None:  # truncate long patterns
                found = True
                s = s + " {pattern = " + pattern.arg + "}"
        return s

    s = get_nontypedefstring(node)

    if s != "":
        t = node.search_one("type")
        # chase typedef
        type_namespace = None
        i_type_name = None
        name = t.arg
        if name.find(":") == -1:
            prefix = None
        else:
            [prefix, name] = name.split(":", 1)
        if prefix is None or t.i_module.i_prefix == prefix:
            # check local typedefs
            pmodule = node.i_module
            typedef = statements.search_typedef(t, name)
        else:
            # this is a prefixed name, check the imported modules
            err = []
            pmodule = statements.prefix_to_module(t.i_module, prefix, t.pos, err)
            if pmodule is None:
                return
            typedef = statements.search_typedef(pmodule, name)
        if typedef != None:
            s = s + get_nontypedefstring(typedef)
    return s


def action_params(action):
    s = ""
    for params in action.substmts:

        if params.keyword == "input":
            inputs = params.search("leaf")
            inputs += params.search("leaf-list")
            inputs += params.search("list")
            inputs += params.search("container")
            inputs += params.search("anyxml")
            inputs += params.search("uses")
            for i in inputs:
                s += " in: " + i.arg + "\n"

        if params.keyword == "output":
            outputs = params.search("leaf")
            outputs += params.search("leaf-list")
            outputs += params.search("list")
            outputs += params.search("container")
            outputs += params.search("anyxml")
            outputs += params.search("uses")
            for o in outputs:
                s += " out: " + o.arg + "\n"
    return s


def get_folder_css():
    return """
background:url(data:image/gif;base64,R0lGODlhGgAOALMLAJmZmYuLi3p6ev///+zs7MzMzGZmZqqqqrS0tLq6uuHh4f///wAAAAAAAAAAAAAAACH5BAEAAAsALAAAAAAaAA4AAASJcMlJq714qgROKUtxAABBgJkUFMQwFEhyFoFAKini7idSHwGDQXAYYAADxQdBOjiBQqGgYKx4AomCYoYAHqLRVVUCKCBdSthhCgYDKIDuTpnoGgptgxged3FHBgpgU2MTASsmdCM1gkNFGDVaHx91QQQ3KZGSZocHBCEpEgIrCYdxn6EVAnoIGREAOw==)  no-repeat; float: left; padding-right: 30px;margin-left: 3px;
          """


def get_doc_css():
    return """
background:url(data:image/gif;base64,R0lGODlhDAAOALMJAMzMzODg4P///+np6a+vr+7u7jMzM5mZmYmJif///wAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAAkALAAAAAAMAA4AAARFEEhyCAEjackPCESwBRxwCKD4BSSACCgxrKyJ3B42sK2FSINgsAa4AApI4W5yFCCTywts+txJp9TC4IrFcruwi2FMLgMiADs=)
no-repeat; float: left; padding-right: 10px; margin-left: 3px;
cursor: pointer;
          """


def get_leaf_css():
    return """
background:url(data:image/gif;base64,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)
no-repeat; float: left; padding-right: 10px;margin-left: 3px;
          """


def get_leaf_list_css():
    return """
background:url(data:image/gif;base64,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)
no-repeat; float: left; padding-right: 10px; margin-left: 3px;
          """


def get_action_css():
    return """
background:url(data:image/gif;base64,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)
no-repeat; float: left; height: 14px; width: 12px; padding-right: 10px; margin-left: 3px;
          """


def get_openconfig_logo():
    return """ "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJoAAAAjCAYAAABsOhOqAAAABGdBTUEAALGPC/xh
BQAADpVJREFUeAHtnAtwVcUZgO+9eUDI+ICCOJgbCASSFoJAUEFRUJTHKMgU4pTW
gNIaEaWxrdYqgw20imIV245YBYQAvnjUMqIQlIJFDT54GAyBJATzgNKCgATyICS3
33+4e9lz7jk3Cc1YS+7ObHb3f+3+//777+NccLvOM63zeje7fL6hVna3271mVHn5
OCs83G7dFvCct/o+X28HXq8DPAxuxRYI6WgfJiVdZGebnB49LgPe0Q5HlIuzhYeB
rdoCjo6W4/X+qPLUqQM58fEZVgv5amsHWGFau9PWxMSLtXa4GraAy21ng5y4uJ80
uFzZ4CIED9HqWI/nniqXa4jP53uIPASwo5NCfxL8WxEREXNuKS0tEBnh1LotEORo
6+PjJ/kaGhZjFrMjud3VbIsxzTQX/ura3LZt28k3FhdXNJM3TH4BWcDkTNwk77J1
MlG4+U4mXB6X291pWFHRAWmEU+u1QKRS/eO4uJgTLtezPmskUwTmsp5QuMXt8eQ0
+HylHrf7COhLyIm0b8Qpb6aunHgOTx6IDafWbAHT1unfNrNDGEQc7BUcK2tEeflB
JzouEn3YM2dDmzJy0KBk98qV9U60YXjrsIDJ0UTl9V7vGg77Y23UP4KDjR9ZXv4P
hUtMTOzU0NDQl4jVA559Ho8nr7i4+LDCy+1zUHExgfLCSqmpqVHHjh1LRucr0ayG
M+hnBQUFpReWli2rTZCjrUtISHLV1e2xdHMk2u0eNLy8fJ/Au3fvfjfFbAwd9GaG
01WQZ+7bt2+J0F5ICb3j0ecF8gh0j9Z1Q+fDwDa1a9cuMz8//5COC9eNlwuzGdj2
ZnDO+r0GrSeS3SSRrEePHl4i2AJwIzW8UzWHCHcPDleuE/Ts2fOGM2fOyIOvnmp5
CpELQ7keEXUCBz6dxKgjpwQZ26Wh87Rp0+bzPXv2fGUQWf7gQPJsc7mAo6Kiviws
LLQuNFlcU0HPhc72EVuJxOH+RZ6I3psUTC+x4WXY8BpgshMkUBaT86Kjoz9hfF/r
tKreq1evjnV1dcOkDU9VSUnJuwqnlykpKe1Pnjw53E/ng261wuu2UDC7smvXrms3
b95co/fJPNajz1t29NjDjW2uguZK6hLhaxnjLto7i4qKdioeU0TzpaVFrN+6tYLD
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
MOIAAAAASUVORK5CYII=" """


def get_folder_open_img():
    return """url(data:image/gif;base64,R0lGODlhGgAOALMLAJmZmYqKiv///+zs7MzMzGZmZrOzs7q6uqqqqnZ2duHh4f///wAAAAAAAAAAAAAAACH5BAEAAAsALAAAAAAaAA4AAASScMlJq714qgMMIQuBAMAwZBRADIJAGMfwBQE6GW0uGzRS2wuAQPHhABAIAyBAABSe0IJKgiAEDgSF7OVDBKNQwEQlbBG5CZAiAA4oxsoc8WBAFEALe9SQ6rS2dU5vCwJsTwECKUwmcyMBCYMhUHgTj1kfRTwFJxKFBYgVlpdNNCUVBHcWCUwHpQacFgJCqp98GBEAOw==)"""


def get_folder_closed_img():
    return """url(data:image/gif;base64,R0lGODlhGgAOALMLAJmZmYuLi3p6ev///+zs7MzMzGZmZqqqqrS0tLq6uuHh4f///wAAAAAAAAAAAAAAACH5BAEAAAsALAAAAAAaAA4AAASJcMlJq714qgROKUtxAABBgJkUFMQwFEhyFoFAKini7idSHwGDQXAYYAADxQdBOjiBQqGgYKx4AomCYoYAHqLRVVUCKCBdSthhCgYDKIDuTpnoGgptgxged3FHBgpgU2MTASsmdCM1gkNFGDVaHx91QQQ3KZGSZocHBCEpEgIrCYdxn6EVAnoIGREAOw==)"""


def get_leaf_img():
    return """url(data:image/gif;base64,R0lGODlhGgAOALMLAJmZmYuLi3p6ev///+zs7MzMzGZmZqqqqrS0tLq6uuHh4f///wAAAAAAAAAAAAAAACH5BAEAAAsALAAAAAAaAA4AAASJcMlJq714qgROKUtxAABBgJkUFMQwFEhyFoFAKini7idSHwGDQXAYYAADxQdBOjiBQqGgYKx4AomCYoYAHqLRVVUCKCBdSthhCgYDKIDuTpnoGgptgxged3FHBgpgU2MTASsmdCM1gkNFGDVaHx91QQQ3KZGSZocHBCEpEgIrCYdxn6EVAnoIGREAOw==)"""
