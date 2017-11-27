
#!/usr/bin/env bash
python setup.py install
git clone --recursive https://github.com/PyBossa/pybossa.git
cd pybossa
pip install -U pip
pip install -r requirements.txt
cd ..
pip install --editable pybossa
