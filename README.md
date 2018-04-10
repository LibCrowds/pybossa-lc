# pybossa-lc

[![Build Status](https://travis-ci.org/LibCrowds/pybossa-lc.svg?branch=master)](https://travis-ci.org/LibCrowds/pybossa-lc)

> A PYBOSSA plugin for managing LibCrowds projects.

The plugin is designed to work in conjunction with the
[LibCrowds frontend](https://github.com/LibCrowds/libcrowds) and contains
functions for generating LibCrowds projects and analysing their results.

Key features:

- Analyses task run data and stores final results as Web Annotations
- Defines a templating system for configuring and generating projects
- Enables the creation of projects with parent-child relationships
- Replaces default PYBOSSA emails with custom templates
- Enables generating of custom data downloads

For details of how project creation and results analysis works in LibCrowds,
see the [**LibCrowds Documentation**](https://docs.libcrowds.com).

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

If your database is already populated when installing this plugin you may
need to run the migration functions in [cli](cli); see each module and
it's associated docstring for details.

## Configuration

The following settings should be added to your main PYBOSSA configuration file:

``` python
# SPA server name
SPA_SERVER_NAME = 'http://example.com'
```

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
