#!/usr/bin/env bash
set -e

echo "Creating files..."
mkdir -p .auklet htmlcov

filelist="local.txt version communication usage limits"
for file in $filelist
do
    touch .auklet/$file
done

touch key.pem
zip key.pem.zip key.pem

git clone https://github.com/pyenv/pyenv.git ./.pyenv
export PYENV_ROOT="./.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

git clone https://github.com/momo-lab/pyenv-install-latest.git "$(pyenv root)"/plugins/pyenv-install-latest

# When another major or minor python version gets released or if a version
# gets depreciated, add the version in the format major.minor (EX. 3.4)
# or delete the version after depreciation to discontinue support and testing
VERSIONLIST="2.7 3.7"
for VERSION in $VERSIONLIST
do
    pyenv install-latest $VERSION
    LATEST_VERSION=$(pyenv versions | grep $VERSION | grep -vE "(2.7.12|3.5.2|system)")
    pyenv global $LATEST_VERSION

    pyver=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    echo Python $pyver

    pip install --upgrade pip
    pip install -U setuptools
    pip install -r tests.txt

    python setup.py install

    COVERAGE_FILE=.coverage.python$pyver coverage run --rcfile=".coveragerc" setup.py test
done

coverage combine
coverage report -m
sudo chown circleci:circleci htmlcov
coverage html -d htmlcov
coverage xml

rm -Rf .auklet .pyenv .cache
rm -f cc-test-reporter key.pem key.pem.zip