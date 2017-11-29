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
cd /path/to/pybossa/pybossa/plugins
git clone https://github.com/LibCrowds/pybossa-lc
cp -r pybossa-lc/pybossa_lc pybossa_lc
```

The plugin will be available after you restart the server.

## Testing

This plugin relies on core functions PYBOSSA, therefore the easiest way to test
it is use the PYBOSSA testing environment.

``` bash
# clone PYBOSSA
git clone --recursive https://github.com/Scifabric/pybossa.git

# start the environment
cd pybossa
vagrant up

# enter the environment
vagrant ssh

# clonse pybossa-lc
git clone https://github.com/LibCrowds/pybossa-lc

# change directory
cd pybossa-lc

# test
nosetests test/
```
