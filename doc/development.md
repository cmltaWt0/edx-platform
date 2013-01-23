# Development Tasks

## Prerequisites

### Ruby

To install all of the libraries needed for our rake commands, run `bundle install`.
This will read the `Gemfile` and install all of the gems specified there.

### Python

In order, run the following:

    pip install -r pre-requirements.txt
    pip install -r requirements.txt
    pip install -r test-requirements.txt

### Binaries

Install the following:

* Mongodb (http://www.mongodb.org/)

### Databases

First start up the mongo daemon. E.g. to start it up in the background
using a config file:

    mongod --config /usr/local/etc/mongod.conf &

Check out the course data directories that you want to work with into the
`GITHUB_REPO_ROOT` (by default, `../data`). Then run the following command:

    rake resetdb

## Starting development servers

Both the LMS and Studio can be started using the following shortcut tasks

    rake lms  # Start the LMS
    rake cms  # Start studio
    rake lms[cms.dev]  # Start LMS to run alongside Studio
    rake lms[cms.dev_preview]  # Start LMS to run alongside Studio in preview mode

Under the hood, this executes `django-admin.py runserver --pythonpath=$WORKING_DIRECTORY --settings=lms.envs.dev`,
which starts a local development server.

Both of these commands take arguments to start the servers in different environments
or with additional options:

    # Start the LMS using the test configuration, on port 5000
    rake lms[test,5000]  # Executes django-admin.py runserver --pythonpath=$WORKING_DIRECTORY --setings=lms.envs.test 5000

*N.B.* You may have to escape the `[` characters, depending on your shell: `rake "lms[test,5000]"`

## Running tests

### Python Tests

This runs all the tests (long, uses collectstatic):

    rake test

If if you aren't changing static files, can run `rake test` once, then run

    rake fasttest_lms

or

    rake fasttest_cms
    
xmodule can be tested independently, with this:

    rake test_common/lib/xmodule

To run a single django test class:

    django-admin.py test --settings=lms.envs.test --pythonpath=. lms/djangoapps/courseware/tests/tests.py:TestViewAuth

To run a single django test:

    django-admin.py test --settings=lms.envs.test --pythonpath=. lms/djangoapps/courseware/tests/tests.py:TestViewAuth.test_dark_launch


To run a single nose test file:

    nosetests common/lib/xmodule/xmodule/tests/test_stringify.py

To run a single nose test:

    nosetests common/lib/xmodule/xmodule/tests/test_stringify.py:test_stringify


Very handy: if you uncomment the `--pdb` argument in `NOSE_ARGS` in `lms/envs/test.py`, it will drop you into pdb on error.  This lets you go up and down the stack and see what the values of the variables are.  Check out http://docs.python.org/library/pdb.html


### Javascript Tests

These commands start a development server with jasmine testing enabled, and launch your default browser
pointing to those tests

    rake browse_jasmine_{lms,cms}

To run the tests headless, you must install phantomjs (http://phantomjs.org/download.html).

    rake phantomjs_jasmine_{lms,cms}

If the `phantomjs` binary is not on the path, set the `PHANTOMJS_PATH` environment variable to point to it
    
    PHANTOMJS_PATH=/path/to/phantomjs rake phantomjs_jasmine_{lms,cms}


## Getting More Information

Run the following to see a list of all rake tasks available and their arguments

    rake -T

## Testing using queue servers

When testing problems that use a queue server on AWS (e.g. sandbox-xqueue.edx.org), you'll need to run your server on your public IP, like so.

`django-admin.py runserver --settings=lms.envs.dev --pythonpath=. 0.0.0.0:8000`

When you connect to the LMS, you need to use the public ip.  Use `ifconfig` to figure out the numnber, and connect e.g. to `http://18.3.4.5:8000/`


## Content development

If you change course content, while running the LMS in dev mode, it is unnecessary to restart to refresh the modulestore.  

Instead, hit /migrate/modules to see a list of all modules loaded, and click on links (eg /migrate/reload/edx4edx) to reload a course.

### Gitreload-based workflow

github (or other equivalent git-based repository systems) used for
course content can be setup to trigger an automatic reload when changes are pushed.  Here is how:

1. Each content directory in mitx_all/data should be a clone of a git repo

2. The user running the mitx gunicorn process should have its ssh key registered with the git repo

3. The list settings.ALLOWED_GITRELOAD_IPS should contain the IP address of the git repo originating the gitreload request.
    By default, this list is ['207.97.227.253', '50.57.128.197', '108.171.174.178'] (the github IPs).
    The list can be overridden in the startup file used, eg lms/envs/dev*.py

4. The git post-receive-hook should POST to /gitreload with a JSON payload.  This payload should define at least

   { "repository" : { "name" : reload_dir }

    where reload_dir is the directory name of the content to reload (ie mitx_all/data/reload_dir should exist)

    The mitx server will then do "git reset --hard HEAD; git clean -f -d; git pull origin" in that directory.  After the pull,
    it will reload the modulestore for that course.

Note that the gitreload-based workflow is not meant for deployments on AWS (or elsewhere) which use collectstatic, since collectstatic is not run by a gitreload event.

Also, the gitreload feature needs MITX_FEATURES['ENABLE_LMS_MIGRATION'] = True in the django settings.

