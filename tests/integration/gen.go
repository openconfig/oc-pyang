package main

import (
	"bytes"
	"flag"
	"fmt"
	"path/filepath"
	"sort"
	"strings"
	"text/template"

	log "github.com/golang/glog"

	"github.com/openconfig/models-ci/commonci"
)

var (
	modelRepoPath = flag.String("path", "", "Path to openconfig/public repo to parse models from")
)

// mustTemplate generates a template.Template for a particular named source template
func mustTemplate(name, src string) *template.Template {
	return template.Must(template.New(name).Parse(src))
}

var tmpl = mustTemplate("bash", `
#!/bin/bash

export PLUGIN_DIR=$(/usr/bin/env python -c \
      'import openconfig_pyang; import os; \
       print("{}/plugins".format(os.path.dirname(openconfig_pyang.__file__)))')

FAIL=0

{{ range $cmd := .Cmds }}
log=$({{ $cmd }})
res=$(echo $?)
if [ $res -ne 0 ]; then
	echo ${log}
	FAIL=$((FAIL+1))
fi
{{ end }}

if [ $FAIL -ne 0 ]; then
	exit 127
fi`)

func main() {
	flag.Parse()

	if *modelRepoPath == "" {
		log.Exitf("FATAL: specify OpenConfig model path, got: %q", *modelRepoPath)
	}

	modelMap, err := commonci.ParseOCModels(*modelRepoPath)
	if err != nil {
		log.Exitf("cannot read OpenConfig models, %v", err)
	}

	modelDirNames := make([]string, 0, len(modelMap.ModelInfoMap))
	for modelDirName := range modelMap.ModelInfoMap {
		modelDirNames = append(modelDirNames, modelDirName)
	}
	sort.Strings(modelDirNames)

	cmds := []string{}
	for _, n := range modelDirNames {
		for _, m := range modelMap.ModelInfoMap[n] {
			if !m.RunCi {
				continue
			}
			files := []string{}

			dirParts := strings.Split(n, ":")
			if len(dirParts) < 2 {
				log.Errorf("cannot parse directory %v, expected >2 elements", dirParts)
				continue
			}
			dir := filepath.Join(dirParts[0 : len(dirParts)-1]...)
			for _, f := range m.BuildFiles {
				parts := strings.Split(f, "/")
				if len(parts) < 2 {
					log.Errorf("invalid filename %v, expected >2 parts", parts)
					continue
				}
				fn := filepath.Join(parts[1:]...)
				files = append(files, filepath.Join(modelMap.ModelRoot, dir, fn))
			}
			cmds = append(cmds, fmt.Sprintf("pyang --plugindir $PLUGIN_DIR --openconfig --oc-only -p %s -p %s/third_party/ietf %s", modelMap.ModelRoot, modelMap.ModelRoot, strings.Join(files, " ")))
		}
	}

	b := &bytes.Buffer{}
	if err := tmpl.Execute(b, struct{ Cmds []string }{Cmds: cmds}); err != nil {
		log.Exitf("cannot generate script, %v", err)
	}
	fmt.Printf("%s\n", b.String())
}
