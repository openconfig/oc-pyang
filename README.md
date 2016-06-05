# oc-pyang
OpenConfig plugins for pyang

Plugins for the [pyang](https://github.com/mbj4668/pyang) YANG parser / compiler for working with
OpenConfig and other YANG data models.

## Contents
* *openconfig.py* - pyang plugin to check OpenConfig YANG [style guidelines](https://github.com/openconfig/public/blob/master/doc/openconfig_style_guide.md)
* *yangpath.py* - pyang plugin to list and analyze schema paths in YANG modules

## Using the plugins

1. Install [pyang](https://github.com/mbj4668/pyang) (plugins have been developed and tested for pyang v1.6)

2. Clone / download this repository

3. `pyang --plugindir <.../path/to/repo/plugins> <options> <YANG modules>`
  * `pyang --plugindir <.../path/to/repo/plugins> --help` to see options

#### Note: these files are not part of any official Google product
