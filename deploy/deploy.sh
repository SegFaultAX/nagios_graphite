virtualenv-2.7 #{VIRTUALENV}
#{VIRTUALENV}/bin/pip install -U pip -i #{PYPI}
#{VIRTUALENV}/bin/pip install -r requirements.txt
/bin/bash -c /usr/bin/python2.7 setup.py bdist_rpm --release ${GO_STAGE_COUNTER} --fix-python
/bin/bash -c /usr/bin/ox-upload-artifact -r libs-snapshot-local -p python2.7/pypi -n dist/*.noarch.rpm --verbose
