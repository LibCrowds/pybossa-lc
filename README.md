# pybossa-lc

[![Build Status](https://travis-ci.org/LibCrowds/pybossa-lc.svg?branch=master)](https://travis-ci.org/LibCrowds/pybossa-lc)

> A PYBOSSA plugin for managing LibCrowds projects.

The plugin is designed to work in conjunction with the
[LibCrowds frontend](https://github.com/LibCrowds/libcrowds). It contains
functions for generating LibCrowds projects and analysing their results.

While some of this could be handled purely via the API it's important that we
keep the content of the project templates etc. in sync, so some forms are
provided for project creation and management via a system of templates.

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

## Configuration

The following settings should be added to your main PYBOSSA configuration file:

``` python
# SPA server name
SPA_SERVER_NAME = 'http://example.com'

# The user ID used to make automated announcements
ANNOUNCEMENT_USER_ID = 1

# Additional startup tasks
EXTRA_STARTUP_TASKS = {
    'check_for_missing_templates': False,
    'populate_empty_results': False,
    'reanalyse_all_results': False,
    'remove_bad_volumes': False
}
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
