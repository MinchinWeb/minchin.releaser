Minchin.Releaser
================

|PyPI Version badge| |Changelog badge|

.. |PyPI Version badge| image:: https://img.shields.io/pypi/v/minchin.releaser
   :target: https://pypi.org/project/minchin.releaser/

.. |Changelog badge| image:: https://img.shields.io/badge/-Changelog-success
   :target: https://github.com/MinchinWeb/minchin.releaser/blob/master/changelog.rst

Tools to make releasing Python packages easier.

*Minchin dot Releaser* in currently set up as an
`invoke <http://www.pyinvoke.org/>`_ task. It is designed to provide a single
command to make and publish a release of your Python package. An extra
configuration file is an one-time set up requirement to be able to make use of
this.

Once set up, *Minchin dot Releaser*, when run, will:

- check the configuration
- confirm all items in the project directory have been added to Git (i.e. that
  the repo is clean)
- check that your Readme will render on PyPI
- sort your import statements
- vendorize required packages
- run the test suite
- update the version number within your code
- add the release to your changelog
- build project documentation
- build your project as a Python distribution
- confirm your project can be installed from the local machine to the local
  machine
- confirm your project can be uploaded to the test PyPI server and then
  downloaded and installed from this server.
- confirm your project can be uploaded to the main PyPI server and then
  downloaded and installed from this server.
- create a Git tag for your release
- update your version number to a pre-release version

*Minchin dot Releaser* relies on features added in the more recent versions of
Python, and thus is Python 3 only.

Assumptions
-----------

This package makes several assumptions. This is not the only way to do these
things, but I have found these choices work well for my use-cases. If you have
chosen a different way to set up your project, most of the applicable features
will just not work, but the rest of *Minchin dot Releaser* should continue to
work.

It is assumed:

- this is a Python project.
- your version is stored in one place in your project, as a string assigned to
  the variable ``__version__``, that this is one line and there is nothing else
  on this line. If this is not the case, *Minchin dot Releaser* will be unable
  to determine your project's version number and so won't be much use to you.
  This is the project's one hard requirement in how you organize your code.
- your version number is importable by Python at
  ``<some_module_name>.__version__``.
- source control is done using Git. The Git functionality will be ignored if
  this is not the case.

Setting Up Your Project
-----------------------

Step 1. Install ``minchin.releaser``.
"""""""""""""""""""""""""""""""""""""

The simplest way is to use ``pip``::

    pip install minchin.releaser

This will also install all the other packages ``minchin.releaser`` depends
on.

You will also want to add ``minchin.releaser`` to the list of your
project's requirements.

Step 2. Create a ``tasks.py`` file.
"""""""""""""""""""""""""""""""""""

This is where ``invoke`` determine was tasks are available to run. This file
should be created in the root folder of your project. If you are not using
``invoke`` for other tasks, this file can be two lines:

.. code-block:: python

    # tasks.py

    import invoke

    from minchin.releaser import make_release

To confirm that this is working, go to the command line in the root folder
of your project, and run:

.. code-block:: sh

    $ invoke --list

which will now list ``make_release`` as an available task.

Step 3. Configure your project.
"""""""""""""""""""""""""""""""

Project configuration is actually ``invoke`` configuration, so it is stored
in the ``invoke.yaml`` folder in the project root (or anywhere else
``invoke`` can load configuration from) under the ``releaser`` key.

Available sub-keys:

module_name
    (required) the name of your project. It is assumed that your project's
    version number is importable at ``module_name.__version__`` (see
    project assumptions).
pypi_name
    (optional) the name of your project as uploaded to PyPI. This only needs to
    be set if it differs from ``module_name``.
here
    (required) the base location to build your package from. To set to the
    current directory, set to ``.``
docs
    (required, but can be set to ``None``) the base documentation
    directory. This is relative to ``here``.
test
    (required, but can be set to ``None``) the base test directory. This is
    relative to ``here``.
source
    (required) the base directory of your Python source code. This is
    relative to ``here``.
changelog
    (required, but can be set to ``None``) the location of your changelog
    file. This is relative to ``here``.
version
    (required) the location of where your version string is stored. This is
    relative to ``here``.
test_command
    (required, but can be set to ``None``) command, run from the command
    line with the current directory set to ``here``, to run your test suite.
version_bump
    (optional) default *level* to bump your version. If set to ``none``,
    this will be requested at runtime. Valid options include ``major``,
    ``minor``, ``bug``, and ``none``.
extra_packages
    (optional) Used to install packages before installing your module from
    the server. Useful particularly for packages that need to be installed
    from cache (rather than re-downloaded and compiled each time) or for
    packages that are not available on the test PyPI server. Valid server
    keys are ``local``, ``test``, and ``pypi``. Under the server key,
    create a list of the packages you want explicitly installed.

(vendorize keys are not listed here.)

Step 4. Set up Invoke command shell (Windows).
""""""""""""""""""""""""""""""""""""""""""""""

*Minchin dot Releaser* runs certain commands at the command line. ``Invoke``,
regardless of platform, tries to run these on ``/bin/bash`` which doesn't exist
in Windows and thus these commands fail.

To fix this, create a ``.invoke.yaml`` file in the root of your user directory
(so the file is ``C:\Users\<your_username>\.invoke.yaml``) and add:

.. code-block:: yaml

    run:
        shell: C:\Windows\system32\CMD.exe

Step 5. Set up twine configuration.
"""""""""""""""""""""""""""""""""""

Create or modify ``$HOME/.pypirc`` to include the ``testpypi`` server:

.. code-block:: ini

    [distutils]
    index-servers=
        pypi
        testpypi

    [testpypi]
    repository: https://test.pypi.org/legacy/
    username: your testpypi username

.. warning::

    Do not store passwords in the .pypirc file. Storing passwords in plain text
    is never a good idea.

*Minchin dot Releaser* is automated, and so needs access to your password. This
can be done using ``keyring``. Keyring can be installed by ``pip`` and then
passwords are added from the command-line.

.. code-block:: sh

    $ pip install keyring
    $ keyring set https://test.pypi.org/legacy/ your-username
    $ keyring set https://upload.pypi.org/legacy/ your-username

See `Twine Keyring Support
<https://twine.readthedocs.io/en/latest/#keyring-support>`_ for more details.


Step 6. Register your package on PyPI.
""""""""""""""""""""""""""""""""""""""

(On the new infrastructure, this no longer needs to be done explicitly. Just
upload your package.)

Step 7. Upload your package.
""""""""""""""""""""""""""""

.. code-block:: sh

    $ invoke make_release

And then work through the prompts. If this process breaks half-way through,
you can re-start.


Credits
-------

Inspired (in part) by
https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/


Sample ``invoke.yaml``
----------------------

.. code-block:: yaml

    releaser:
        module_name: minchin.releaser
        here: .
        docs: .
        test: None
        source: minchin
        changelog: changelog.rst
        version: minchin\releaser\constants.py
        test_command: "green -kq"
        version_bump: none
        extra_packages:
            test:
                - gitdb
                - invoke
                - isort
                - pkginfo
                - semantic_version
                - twine
                - wheel
            pypi:
                - invoke
        vendor_dest: minchin\releaser\_vendor
        vendor_packages:
            "minchin.text":
                src: ..\minchin.text\minchin
                dest: .
                requirements: ..\minchin.text\requirements.in
        vendor_override_src: vendor_src
