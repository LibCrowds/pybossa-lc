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
pip install -r test_requirements.txt

# test
nosetests test/
```

# Endpoints

Following are brief details of the endpoints provided by this plugin.

## Users

### List a User's Templates

List all templates created by the user.

```html
GET /libcrowds/users/\<name\>/templates
```

```json
{
  "form": {
    "category_id": null,
    "csrf": "1515172370.21##b668983b3544e9faeaed77a3d08e6403dc919b00",
    "description": null,
    "errors": {},
    "name": null,
    "tutorial": null
  },
  "templates": [
    {
      "id": "c3017984-6885-45a1-81a9-8ba3a18793dc",
      "project": {
        "category_id": 1,
        "description": "This project is amazing",
        "name": "My Project Type",
        "tutorial": "Do stuff"
      },
      "task": null
    }
  ]
}
```

### Add a template

Add a template for the user by posting the form in the above response.

```html
POST /libcrowds/users/\<name\>/templates
```

```json
{
  "flash": "Project template created",
  "next": "/libcrowds/users/tester/templates/12865546-8064-41c8-9be0-1d4f9b5a3182",
  "status": "success"
}
```

### Get a template

Get a template by ID for the owner.

```html
GET /libcrowds/users/<name>/templates/<tmpl_id>
```

```json
{
  "template": {
    "id": "37577f77-fad5-474f-af47-a8a9b2c150eb",
    "project": {
      "category_id": 1,
      "description": "This project is amazing",
      "name": "My Project Type",
      "tutorial": "Do stuff"
    },
    "task": null
  }
}
```

### Update template project data

Update the core project template data.

```html
POST /libcrowds/users/<name>/templates/<tmpl_id>
```

```json

```


### Get the template task data

Update the task data for a template.

```html
GET /libcrowds/users/<name>/templates/<tmpl_id>/tasks
```

```json

```

### Update template project data

Update the project data for a template.

```html
GET /libcrowds/users/<name>/templates/<tmpl_id>/project
```

```json

```
