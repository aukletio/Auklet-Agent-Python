#!/usr/bin/env bash
set -e
CIRCLE_LOCAL_BUILD=$1

#
# This file exists because we should be able to run tests locally without needing
# to download the code climate validation package. To do this we need
# code climate to be in a different file than the test execution.
#
# The test reporter will throw a HTTP 409 error if we rebuild in circle because
# a test report was already posted for that commit. On line 19-30 we have
# implemented a check to see if the test reporter throws this message.

git clone https://github.com/pyenv/pyenv.git ~/.pyenv

sudo pip install tox
sudo pip install --upgrade setuptools

PIL_BIN="$HOME/.pyenv/plugins/pyenv-install-latest/bin/pyenv-install-latest"
curl https://raw.githubusercontent.com/momo-lab/pyenv-install-latest/master/bin/pyenv-install-latest --create-dirs -o $PIL_BIN
chmod +x $PIL_BIN

rm -Rf htmlcov

if [[ "$CIRCLE_LOCAL_BUILD" == 'false' ]]; then
  curl -L https://codeclimate.com/downloads/test-reporter/test-reporter-latest-linux-amd64 > ./cc-test-reporter
  chmod +x ./cc-test-reporter
  ./cc-test-reporter before-build
fi

tox

sudo pip install coverage==4.5.1

coverage combine
coverage report -m
coverage xml
coverage html

if [[ "$CIRCLE_LOCAL_BUILD" == 'false' ]]; then
  CC_TEST_REPORTER_ID='1f241448ca8912db9dfe358e8d182fa2c736af8ba565d2954a3110583c4abd9c'
  # Set -e is disabled momentarily to be able to output the error message to log.txt file.
  set +e
  ./cc-test-reporter after-build -t coverage.py -r $CC_TEST_REPORTER_ID --exit-code $? 2>&1 | tee exit_message.txt
  result=$?
  set -e
  # Then we check the third line and see if it contains the known error message
  # and print an error message of our own but let the build succeed.
  if [ "$(echo `sed -n '2p' exit_message.txt` | cut -d ' ' -f1-5)" = "HTTP 409: A test report" ]; then
    echo "A test report has already been created for this commit; this build will proceed without updating test coverage data in Code Climate."
    exit 0
  else
    exit $result
  fi
fi