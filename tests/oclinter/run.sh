#!/bin/bash
# Copyright 2016 The OpenConfig Authors.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

TESTDIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAIL=0

export PLUGIN_DIR=$(/usr/bin/env python -c \
      'import openconfig_pyang; import os; \
       print("{}/plugins".format(os.path.dirname(openconfig_pyang.__file__)))')

for i in `find $TESTDIR -mindepth 1 -maxdepth 1 -type d`; do
  if [ -e $i/Makefile ]; then
    failed=0

    cd $i
    make ok
    okres=$(echo $?)

    cd $i
    make broken
    borkres=$(echo $?)

    if [ $okres -ne 0 ]; then
      failed=1
    fi

    if [ $borkres -eq 0 ]; then
      failed=1
    fi

    if [ $failed -ne 0 ]; then
      FAIL=$((FAIL+1))
      echo "$i: FAILED"
    else
      echo "$i: OK"
    fi
  fi
done

if [ $FAIL -ne 0 ]; then
  echo "test fail: $FAIL tests failed"
  exit 127
else
  echo "test succeeded"
  exit 0
fi
