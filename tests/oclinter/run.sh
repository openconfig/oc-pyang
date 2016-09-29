#!/bin/bash

TESTDIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAIL=0

export PLUGIN_DIR=$(/usr/bin/env python -c \
      'import openconfig_pyang; import os; \
        print "%s/plugins" % \
          os.path.dirname(openconfig_pyang.__file__)')

for i in `find $TESTDIR -mindepth 1 -maxdepth 1 -type d`; do
  if [ -e $i/Makefile ]; then
    failed=0

    okres=$(cd $i; make ok &>/dev/null; echo $?)
    borkres=$(cd $i; make broken &>/dev/null; echo $?)

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
