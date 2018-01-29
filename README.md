# pybossa-lc

[![Build Status](https://travis-ci.org/LibCrowds/pybossa-lc.svg?branch=master)](https://travis-ci.org/LibCrowds/pybossa-lc)

> A PYBOSSA plugin for managing LibCrowds projects.

The plugin is designed to work in conjunction with the
[LibCrowds frontend](https://github.com/LibCrowds/libcrowds). It contains
functions for generating LibCrowds projects and analysing their results. While
some of this could be handled purely via the API it's important that we keep
the content of the project templates etc. in sync, so some forms are provided
for template creation and management.

For details of how project creation and results analysis works in LibCrowds,
see the [**LibCrowds Documentation**](https://docs.libcrowds.com).

Details of the endpoints made available by this plugin are given below for
reference.

## Installation

``` bash
cd /path/to/pybossa/pybossa/plugins
git clone https://github.com/LibCrowds/pybossa-lc
cp -r pybossa-lc/pybossa_lc pybossa_lc
source ../../env/bin/activate
cd pybossa-lc
pip install -r requirements.txt
```

The plugin will be available after you restart the server.

## Testing

As this plugin relies on core functions of PYBOSSA the easiest way to test
it is use the PYBOSSA testing environment.

``` bash
# setup PYBOSSA
git clone --recursive https://github.com/Scifabric/pybossa.git
cd pybossa
vagrant up
vagrant ssh

# setup pybossa-lc
git clone https://github.com/LibCrowds/pybossa-lc
cd pybossa-lc
pip install -r requirements.txt

# test
nosetests test/
```
