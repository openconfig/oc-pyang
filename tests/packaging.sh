#!/bin/bash

TESTDIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd $TESTDIR/..
rm -rf $TESTDIR/tvirtenv $TESTDIR/../dist $TESTDIR/../build $TESTDIR/../openconfig_pyang.egg-info

echo "packaging..."
(cd $TESTDIR/..
python setup.py bdist_wheel sdist >/dev/null
if [ $? -ne 0 ]; then
  echo "Cannot run tests, packaging broken."
  exit 127
fi)

echo "creating virtualenv..."
virtualenv $TESTDIR/tvirtenv >/dev/null
source $TESTDIR/tvirtenv/bin/activate

echo "installing package..."
$TESTDIR/tvirtenv/bin/pip install -r $TESTDIR/../requirements.txt
if [ $? -ne 0 ]; then
  echo "Cannot run tests, installing requirements failed";
  exit 127
fi

$TESTDIR/tvirtenv/bin/pip install $TESTDIR/../dist/openconfig_pyang*.whl
if [ $? -ne 0 ]; then
  echo "Cannot run tests, installing module failed";
  exit 127
fi

FAIL=0
for TEST in oclinter; do
  echo "running test $TEST..."
  (cd /tmp; $TESTDIR/$TEST/run.sh)
  if [ $? -ne 0 ]; then
    FAIL=1
  fi
done

if [ $FAIL -ne 0 ]; then
  echo "Tests failed."
  exit 127
fi
echo "Tests succeeded"

