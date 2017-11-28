# pybossa-lc

[![Build Status](https://travis-ci.org/LibCrowds/pybossa-lc.svg?branch=master)](https://travis-ci.org/LibCrowds/pybossa-lc)

> A PYBOSSA plugin for managing LibCrowds projects.

The plugin is designed to work in conjunction with the
[LibCrowds frontend](https://github.com/LibCrowds/libcrowds). For details
of usage, including descriptions of how the analysis functions work, see the
[**LibCrowds Documentation**](https://docs.libcrowds.com).

## Installation

``` bash
# clone
git clone https://github.com/LibCrowds/pybossa-lc /path/to/pybossa/pybossa/plugins

# activate PYBOSSA virtual environement
source /path/to/pybossa/pybossa/env/bin/activate

# install the plugin
cd /path/to/pybossa/pybossa/plugins/pybossa-lc
python setup.py install
cd ..
cp -r pybossa-lc/pybossa_lc pybossa_lc
```

## Testing

``` bash
# activate a virtual environment
virtualenv env
source env/bin/activate

# setup an instance of PYBOSSA
bin/setup_pybossa.sh

# test
nosetests test/

# lint
pip install pycodestyle
pycodestyle
```
