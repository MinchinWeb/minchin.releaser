Changelog
=========

- :release:`0.8.1 <2021-07-07>`
- :bug:`-` allow PEP518 builds on the test PyPI server.
- :release:`0.8.0 <2021-07-05>`
- :bug:`- major` better cross-platform suport
- :feature:`-` support differing ``module_name`` and ``pypi_name``.
- :release:`0.7.5 <2021-06-02>`
- :bug:`-` don't copy ``.git`` folder when vendorizing a package
- :support:`-` better bootstraping when starting fresh
- :bug:`-` don't include `vendor_src` folder in final distributions
- :bug:`-` better cross-platform suport
- :release:`0.7.4 <2021-04-30>`
- :bug:`-` fix readme rendering
- :release:`0.7.3 <2021-04-30>`
- :bug:`8` update minimum requirements.txt (also #9)
- :bug:`-` update internal version of ``minchin.text`` to 6.1.0
- :release:`0.7.2 <2020-07-16>`
- :bug:`-` support ``isort`` version 5
- :bug:`-` update internal version of ``minchin.text`` to 6.0.2
- :release:`0.7.1 <2020-04-10>`
- :bug:`2` update requirements.txt (also #5)
- :bug:`-` update internal version of ``minchin.text`` to 6.0.1
- :bug:`-` fix Test PyPI urls
- :release:`0.7.0 <2019-02-08>`
- :feature:`-` update internal version of ``minchin.text`` (this library is
  vendorized because otherwise it creates a circular dependency).
- :bug:`- major` rely only on internal version of ``minchin.text``
- :release:`0.6.1 <2018-10-25>`
- :bug:`-` add note that this package is Python 3 only
- :bug:`-` readme rendering check is now part of ``twine``. See `twine
  documentation <https://packaging.python.org/guides/making-a-pypi-friendly-readme/#validating-restructuredtext-markup>`_.
- :release:`0.6.0 <2018-09-19>`
- :feature:`-` check readme rendering to avoid broken PyPI readmes.
- :feature:`-` generate ```requirements.txt`` directly from ``setup.py`` as
  *pip-tools* now supports this.
- :release:`0.5.5 <2018-09-19>`
- :bug:`-` add documentation on how to set up ``twine``.
- :bug:`-` update to new test PyPI url
- :release:`0.5.4 <2017-08-27>`
- :bug:`-` update to new PyPI url
- :release:`0.5.3 <2017-06-24>`
- :bug:`-` properly specify the server for uploading
- :release:`0.5.2 <2017-06-23>`
- :bug:`-` fix flow on creating Git tags with pre-release versions
- :bug:`-` display error if configuration key doesn't exist
- :support:`-` better documentation
- :release:`0.5.1 <2017-05-27>`
- :bug:`-` allow twine to pick the PyPI server to upload to
- :bug:`-` fixes in vendorizing ``minchin.text``, particularly its requirements
- :release:`0.5.0 <2017-04-18>`
- :feature:`-` offer to create Git Tag
- :release:`0.4.2 <2017-04-17>`
- :feature:`-` include vendorized version of ``minchin.text`` to ease with
  install issues
- :feature:`-` add ``vendorize`` script
- :feature:`-` warn if releasing with a pre-release version number
- :feature:`-` allow specifying bump level at run time
- :feature:`-` check (select) configuration keys for existence before proceeding
  with the rest of the script
- :feature:`-` offer to bump version to pre-release at end of process
- :feature:`-` provide summary of test installs
- :feature:`-` consolidate requirements to ``requirements.in``, and generate
  other requirement lists from here
- :release:`0.3.1 <2017-01-29>`
- :bug:`-` don't blow up if uploading fails (this is common when we have
  to retry our upload)
- :bug:`-` always open and write version file with UTF-8 codec
- :release:`0.3.0 <2017-01-29>`
- :feature:`-` test install-ability of module
- :feature:`-` run documentation generation
- :feature:`-` allow overriding version bump level from command line
- :feature:`-` sort import statements
- :feature:`-` run test suite
- :release:`0.2.2 <2016-11-28>`
- :bug:`-` move configuration to top of script file
- :release:`0.2.1 <2016-11-18>`
- :bug:`-` specify downloading of non-cached version of the package for
  multiple formats can be properly and individually tested.
