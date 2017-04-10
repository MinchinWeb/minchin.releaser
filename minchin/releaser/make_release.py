import os
import re
import shutil
import sys
import textwrap
from pathlib import Path

import colorama
import git  # packaged as 'gitpython'
import invoke
import semantic_version
from invoke import task
from minchin import text
from semantic_version import Version

import isort

from . import __version__

# also requires `twine`

# assumed Invoke configuration file points to Windows Shell

version_re = re.compile(r"__version__ = [\"\']{1,3}(?P<major>\d+)\.(?P<minor>\d+).(?P<patch>\d+)(?:-(?P<prerelease>[0-9A-Za-z\.]+))?(?:\+[0-9A-Za-z-\.]+)?[\"\']{1,3}")
bare_version_re = re.compile(r"__version__ = [\"\']{1,3}([\.\dA-Za-z+-]*)[\"\']{1,3}")
list_match_re = re.compile(r"(?P<leading>[ \t]*)(?P<mark>[-\*+]) +:\w+:")

ERROR_COLOR = colorama.Fore.RED
WARNING_COLOR = colorama.Fore.YELLOW
GOOD_COLOR = colorama.Fore.GREEN
RESET_COLOR = colorama.Style.RESET_ALL

# on Windows, this should be '.exe', but we get away with setting it to
# blank as Windows will (typically) run .exe files without specifying the
# file extension
PIP_EXT = ''

VALID_BUMPS = ['none',
               'prerelease', 'dev', 'development',
               'patch', 'bugfix',
               'minor', 'feature',
               'major', 'breaking']
VALID_BUMPS_STR = ", & ".join([", ".join(VALID_BUMPS[:-1]), VALID_BUMPS[-1]])


def server_url(server_name):
    """Determine the server URL."""
    server_name = server_name.lower()
    if server_name in ["testpypi", "pypitest"]:
        return r"https://testpypi.python.org/pypi"
    elif server_name in ["pypi", ]:
        return r"https://pypi.python.org/pypi"


def update_version_number(ctx, bump=None):
    """
    Update version number.

    Returns a two semantic_version objects (the old version and the current
    version).
    """
    if bump is not None and bump.lower() not in VALID_BUMPS:
        print(textwrap.fill("[{}WARN{}] bump level, as provided on command "
                            "line, is invalid. Trying value given in "
                            "configuration file. Valid values are {}."
                            .format(WARNING_COLOR, RESET_COLOR,
                                    VALID_BUMPS_STR),
                            width=text.get_terminal_size().columns - 1,
                            subsequent_indent=' '*7))
        bump = None
    else:
        update_level = bump

    # Find current version
    temp_file = Path(ctx.releaser.version).resolve().parent / ("~" + Path(ctx.releaser.version).name)
    with temp_file.open(mode='w', encoding='utf-8') as g:
        with Path(ctx.releaser.version).resolve().open(mode='r', encoding='utf-8') as f:
            for line in f:
                version_matches = bare_version_re.match(line)
                if version_matches:
                    bare_version_str = version_matches.groups(0)[0]
                    if semantic_version.validate(bare_version_str):
                        old_version = Version(bare_version_str)
                        print("{}Current version is {}".format(" "*4,
                                                               old_version))
                    else:
                        old_version = Version.coerce(bare_version_str)
                        if not text.query_yes_quit("{}I think the version is {}."
                                                   " Use it?".format(" "*4,
                                                                     old_version),
                                                   default="yes"):
                            exit('[{}ERROR{}] Please set an initial version '
                                 'number to continue.'.format(ERROR_COLOR,
                                                              RESET_COLOR))

                    # if bump level not defined by command line options
                    if bump is None:
                        try:
                            update_level = ctx.releaser.version_bump
                        except AttributeError:
                            print("[{}WARN{}] bump level not defined in "
                                    "configuration. Use key "
                                    "'releaser.version_bump'"
                                    .format(WARNING_COLOR, RESET_COLOR))
                            print(textwrap.fill("{}Valid bump levels are: "
                                                "{}. Or use 'quit' to exit."
                                                .format(" "*7,
                                                        VALID_BUMPS_STR),
                                                width=text.get_terminal_size().columns - 1,
                                                subsequent_indent=' '*7))
                            my_input = input("What bump level to use? ")
                            if my_input.lower() in ['quit', 'q', 'exit']:
                                sys.exit(0)
                            elif my_input.lower() not in VALID_BUMPS:
                                exit("[{}ERROR{}] invalid bump level provided. "
                                     "Exiting...".format(ERROR_COLOR, RESET_COLOR))
                            else:
                                update_level = my_input

                    # Determine new version number
                    if update_level is None or update_level.lower() in ['none']:
                        update_level = None
                    elif update_level is not None:
                        update_level = update_level.lower()

                    if update_level in ['breaking', 'major']:
                        current_version = old_version.next_major()
                    elif update_level in ['feature', 'minor']:
                        current_version = old_version.next_minor()
                    elif update_level in ['bugfix', 'patch']:
                        current_version = old_version.next_patch()
                    elif update_level in ['dev', 'development', 'prerelease']:
                        if not old_version.prerelease:
                            current_version = old_version.next_patch()
                            current_version.prerelease = ('dev', )
                        else:
                            current_version = old_version
                    elif update_level is None:
                        # don't update version
                        current_version = old_version
                    else:
                        exit('[{}ERROR{}] Cannot update version in {} mode'
                             .format(ERROR_COLOR, RESET_COLOR, update_level))

                    print("{}New version is     {}".format(" "*4,
                                                           current_version))

                    # Update version number
                    line = '__version__ = "{}"\n'.format(current_version)
                print(line, file=g, end="")
        #print('', file=g)  # add a blank line at the end of the file
    shutil.copyfile(str(temp_file), str(Path(ctx.releaser.version).resolve()))
    os.remove(str(temp_file))
    return(old_version, current_version)


def build_distribution():
    """Build distributions of the code."""
    result = invoke.run('python setup.py sdist bdist_egg bdist_wheel',
                        warn=True, hide=True)
    if result.ok:
        print("[{}GOOD{}] Distribution built without errors."
              .format(GOOD_COLOR, RESET_COLOR))
    else:
        print('[{}ERROR{}] Something broke trying to package your '
              'code...'.format(ERROR_COLOR, RESET_COLOR))
        print(result.stderr)
        sys.exit(1)


def other_dependencies(ctx, server, environment):
    """Install things that need to be in place before installing the main package."""
    print('** Other Dependencies, based on server', server, '**')
    if 'extra_packages' in ctx.releaser:
        server = server.lower()
        extra_pkgs = []
        if server == "local":
            if 'local' in ctx.releaser.extra_packages:
                extra_pkgs.extend(ctx.releaser.extra_packages.local)
        elif server in ["testpypi", "pypitest"]:
            # these are packages not available on the test server, so install them
            # off the regular pypi server
            if 'test' in ctx.releaser.extra_packages:
                extra_pkgs.extend(ctx.releaser.extra_packages.test)
        elif server in ["pypi"]:
            if 'pypi' in ctx.releaser.extra_packages:
                extra_pkgs.extend(ctx.releaser.extra_packages.pypi)
        else:
            print("** Nothing more to install **")

        for pkg in extra_pkgs:
            result = invoke.run('env{0}{1}{0}Scripts{0}pip{2} install {3}'
                                .format(os.sep, environment, PIP_EXT, pkg),
                                hide=True)
            if result.ok:
                print('{}[{}GOOD{}] Installed {}'.format("", GOOD_COLOR,
                                                         RESET_COLOR, pkg))
            else:
                print('{}[{}WARN{}] Something broke trying to install '
                      'package: {}'.format("", WARNING_COLOR, RESET_COLOR,
                                           pkg))
                print(result.stderr)
                sys.exit(1)


def check_local_install(ctx, version, ext, server="local"):
    """
    Upload and install works?

    Uploads a distribution to PyPI, and then tests to see if I can download and
    install it.
    """
    here = Path(ctx.releaser.here).resolve()
    dist_dir = here / 'dist'

    all_files = list(dist_dir.glob('*.{}'.format(ext)))
    the_file = all_files[0]
    for f in all_files[1:]:
        if f.stat().st_mtime > the_file.stat().st_mtime:
            the_file = f
            # this is the latest generated file of the given version

    environment = 'env-{}-{}-{}'.format(version, ext, server)
    if server == "local":
        pass
    else:
        # upload to server
        print("** Uploading to server **")
        result = invoke.run('twine upload {} -r {}'.format(the_file, server),
                            warn=True)
        if result.failed:
            print(textwrap.fill("[{}ERRO{}] Something broke trying to upload "
                                "your package.\nThis will be the case if you "
                                "have already uploaded it before. To upload "
                                "again, use a different version number "
                                "(including a '+' suffix)."
                                .format(ERROR_COLOR, RESET_COLOR),
                                width=text.get_terminal_size().columns - 1,
                                subsequent_indent=' '*7))
            print(result.stderr)

    # remove directory if it exists
    if (here / 'env' / environment).exists():
        shutil.rmtree('env' + os.sep + environment)
    invoke.run('python -m venv env{}{}'.format(os.sep, environment))
    other_dependencies(ctx, server, environment)
    if server == "local":
        result = invoke.run('env{0}{1}{0}Scripts{0}pip{2} install {3} --no-cache'
                            .format(os.sep, environment, '.exe', the_file),
                            hide=True)
    else:
        #print("  **Install from server**")
        result = invoke.run('env{0}{1}{0}Scripts{0}pip{2} install -i {3} '
                            '{4}=={5} --no-cache'
                            .format(os.sep, environment, '.exe',
                                    server_url(server),
                                    ctx.releaser.module_name, version),
                            hide=True)
        if result.failed:
            print('[{}ERROR{}] Something broke trying to install your package.'
                  .format(ERROR_COLOR, RESET_COLOR))
            print(result.stderr)
            sys.exit(1)
    print("** Test version of installed package **")

    result = invoke.run('env{0}{1}{0}Scripts{0}python{2} -c '
                        'exec("""import {3}\\nprint({3}.__version__)""")'
                        .format(os.sep, environment, '.exe',
                                (ctx.releaser.module_name).strip()))
    test_version = result.stdout.strip()
    # print(test_version, type(test_version), type(expected_version))
    if Version(test_version) == version:
        print('{}{} install {} works!{}'.format(GOOD_COLOR, server, ext,
                                                RESET_COLOR))
    else:
        exit('{}{} install {} broken{}'.format(ERROR_COLOR, server, ext,
                                               RESET_COLOR))


def check_existence(to_check, name, config_key=None, relative_to=None,
                    allow_undefined=False):
    """Determine whether a file or folder actually exists."""
    if allow_undefined and (to_check is None or to_check.lower() == 'none'):
        print("{: <14} -> {}UNDEFINED{}".format(name, WARNING_COLOR,
                                                RESET_COLOR))
        return
    else:
        if config_key is None:
            config_key = 'releaser.' + name
        my_check = Path(to_check).resolve()
        if my_check.exists():
            if relative_to is None:
                printed_path = str(my_check)
            else:
                printed_path = str(my_check.relative_to(relative_to))
                if printed_path != '.':
                    printed_path = '.' + os.sep + printed_path
            print("{: <14} -> {}".format(name, printed_path))
            return
        else:
            print("[{}ERROR{}] '{}', as given, doesn't exist. For configruation "
                  "key '{}', was given: {}".format(ERROR_COLOR, RESET_COLOR, name,
                                                   config_key, to_check))
            sys.exit(1)


@task(optional=['bump', 'skip-isort', 'skip-local', 'skip-test', 'skip-pypi'],
      help={'bump': 'What level to bump the version by. Setting this '
                    'overrides the value set in your configuration. '
                    'Valid bump levels are {}.'.format(VALID_BUMPS_STR),
            'skip-isort': 'Skip applying isort to your files.',
            'skip-local': 'Skip testing by installing from local build '
                          'distribution.',
            'skip-test': 'Skip testing by uploading and installing to test '
                         'PyPI server.',
            'skip-pypi': 'Skip testing by uploading and installing to (the '
                         'real) PyPI server.'})
def make_release(ctx, bump=None, skip_local=False, skip_test=False,
                 skip_pypi=False, skip_isort=False):
    """Make and upload the release."""
    make_release_version = __version__
    colorama.init()
    text.title("Minchin 'Make Release' for Python Projects v{}".format(make_release_version))

    print()
    text.subtitle("Configuration")
    # check for valid configuration
    if 'releaser' not in ctx.keys():
        print("[{}ERROR{}] missing configuration for 'releaser'"
              .format(ERROR_COLOR, RESET_COLOR))
        sys.exit(1)
        # TODO: offer to create configuration file
    if ctx.releaser is None:
        print("[{}ERROR{}] empty configuration for 'releaser' found"
              .format(ERROR_COLOR, RESET_COLOR))
        sys.exit(1)
        # TODO: offer to create configuration file

    # TODO: allow use of default values
    for my_key in ['here',
                   'source',
                   'test',
                   'docs',
                   'version',
                  ]:
        if my_key not in ctx.releaser.keys():
            print("[{}ERROR{}] missing configuration key 'releaser.{}'"
                  .format(ERROR_COLOR, RESET_COLOR, my_key))
            sys.exit(1)

    check_existence(ctx.releaser.here, "base dir", "releaser.here")

    here = Path(ctx.releaser.here).resolve()
    check_existence(ctx.releaser.source, "source", "releaser.source", here)
    check_existence(ctx.releaser.test, "test dir", "releaser.test", here, True)
    check_existence(ctx.releaser.docs, "doc dir", "releaser.docs", here, True)
    check_existence(ctx.releaser.version, "version file", "releaser.version", here)

    print()
    text.subtitle("Git -- Clean directory?")
    try:
        repo = git.Repo(str(here))
    except git.exc.InvalidGitRepositoryError:
        repo = None
        print(textwrap.fill('[{}WARN{}] base directory does not appear to be '
                            'a valid git repo.'.format(WARNING_COLOR,
                                                       RESET_COLOR),
                            width=text.get_terminal_size().columns - 1,
                            subsequent_indent=' '*7))

    if repo is not None:
        if repo.is_dirty():
            print(textwrap.fill('[{}WARN{}] git repo is dirty. You should '
                                'probably commit your changes before '
                                'continuing.'.format(WARNING_COLOR,
                                                     RESET_COLOR),
                                width=text.get_terminal_size().columns - 1,
                                subsequent_indent=' '*7))
            # True = yes, False = Quit
            ans = text.query_yes_quit(' '*7 + 'Continue anyway or quit?',
                                      default="quit")
            if ans is False:
                sys.exit(1)
    print()

    text.subtitle("Sort Import Statements")
    if not skip_isort:
        for f in Path(ctx.releaser.source).resolve().glob('**/*.py'):
            isort.SortImports(f)
            print('.', end="")
        if ctx.releaser.test is not None:
            for f in Path(ctx.releaser.test).resolve().glob('**/*.py'):
                isort.SortImports(f)
                print('.', end="")
        print(' Done!')
    else:
        print("[{}WARN{}] Skipped!".format(WARNING_COLOR, RESET_COLOR))
    print()

    text.subtitle("Run Tests")
    try:
        cmd_none = (ctx.releaser.test_command).lower()
    except AttributeError:
        print("[{}WARN{}] test command not configured. Use key "
              "'releaser.test_command'.".format(WARNING_COLOR, RESET_COLOR))
        cmd_none = 'none'
    if cmd_none != 'none':
        result = invoke.run(ctx.releaser.test_command, warn=True)
        if not result.ok:
            print("[{}WARN{}] the test suite reported errors."
                  .format(WARNING_COLOR, RESET_COLOR))
            ans = text.query_yes_quit(' '*7 + 'Continue anyway or quit?',
                                      default="quit")
            if ans is False:
                sys.exit(1)
    else:
        print('[{}WARN{}] No test command given.'.format(WARNING_COLOR,
                                                         RESET_COLOR))
    print()

    text.subtitle("Update Version Number")
    old_version, new_version = update_version_number(ctx, bump)
    print()

    text.subtitle("Add Release to Changelog")
    if old_version == new_version:
        print("[{}WARN{}] Version hasn't changed. Not updating Changelog."
              .format(WARNING_COLOR, RESET_COLOR))
    else:
        print("[{}WARN{}] I can't do this yet, but you probably should.\n"
              "           Not updating Changelog."
              .format(WARNING_COLOR, RESET_COLOR))
    print()

    text.subtitle("Build Documentation")
    try:
        cmd_none = (ctx.releaser.doc_command).lower()
    except (AttributeError, KeyError):
        print("[{}WARN{}] documentation generation command not configured.\n"
              "           Use key 'releaser.doc_command'."
              .format(WARNING_COLOR, RESET_COLOR))
        cmd_none = 'none'
    if cmd_none != 'none':
        result = invoke.run(ctx.releaser.doc_command, warn=True)
        if not result.ok:
            print("[{}WARN{}] the documentation generation reported errors."
                  .format(WARNING_COLOR, RESET_COLOR))
            ans = text.query_yes_quit(' '*7 + 'Continue anyway or quit?',
                                      default="quit")
            if ans is False:
                sys.exit(1)
    else:
        print('[{}WARN{}] No test command given.'.format(WARNING_COLOR,
                                                         RESET_COLOR))
    print()

    ans = text.query_yes_quit('All good and ready to go?')
    if ans is False:
        sys.exit(1)

    text.subtitle("Build Distributions")
    build_distribution()

    server_list = []
    if not skip_local:
        server_list.append('local')
    if not skip_test:
        server_list.append('testpypi')
    if not skip_pypi:
        server_list.append('pypi')

    for server in server_list:
        for file_format in ["tar.gz", "whl"]:
            print()
            text.subtitle("Test {} Build {}".format(file_format, server))
            check_local_install(ctx, new_version, file_format, server)

    # new_version = update_version_number('prerelease')
