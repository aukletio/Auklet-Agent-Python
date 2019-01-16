#!/bin/bash
set -e
if [[ "$1" == "" ]]; then
  echo "ERROR: env not provided."
  exit 1
fi
ENVDIR=$1
VERSION="$(cat ~/.version)"
VERSION_SIMPLE=$(cat ~/.version | xargs | cut -f1 -d"+")
VERSION_PEP440=$(cat ~/.version440)
export TIMESTAMP="$(date --rfc-3339=seconds | sed 's/ /T/')"

echo 'Deploying to PyPI...'
# Make and upload the distribution.
# Update setuptools so we have a version that supports Markdown READMEs.
# twine is also required.
cp LICENSE auklet/licenses/auklet
sudo pip install -U setuptools twine wheel
sudo python setup.py sdist bdist_wheel
if [[ "$TWINE_REPOSITORY_URL" != "" ]]; then
  twine upload --repository-url $TWINE_REPOSITORY_URL dist/*
else
  twine upload dist/*
fi
