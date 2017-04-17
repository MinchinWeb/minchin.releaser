Changelog
=========

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
