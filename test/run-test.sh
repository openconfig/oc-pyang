#!/bin/bash

TESTDIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p $TESTDIR/.deps
(cd .deps; curl -O https://raw.githubusercontent.com/openconfig/public/master/release/models/openconfig-extensions.yang)

for i in `ls $TESTDIR/*.yang`; do
    pyang --plugindir $TESTDIR/../pyang-plugins --openconfig --strict -p $TESTDIR/.deps $i
done
