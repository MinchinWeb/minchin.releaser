
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import colorama
import git
import semantic_version
from invoke import task
from minchin import text
from semantic_version import Version

from . import __version__

# also requires `twine`

# assumed Invoke configuration file points to Windows Shell

version_re = re.compile(r"__version__ = [\"\']{1,3}(?P<major>\d+)\.(?P<minor>\d+).(?P<patch>\d+)(?:-(?P<prerelease>[0-9A-Za-z\.]+))?(?:\+[0-9A-Za-z-\.]+)?[\"\']{1,3}")
bare_version_re = re.compile(r"__version__ = [\"\']{1,3}([\.\dA-Za-z+-]*)[\"\']{1,3}")
list_match_re = re.compile(r"(?P<leading>[ \t]*)(?P<mark>[-\*+]) +:\w+:")

ERROR_COLOR = colorama.Fore.RED
WARNING_COLOR = colorama.Fore.YELLOW
RESET_COLOR = colorama.Style.RESET_ALL


def server_url(server_name):
    server_name = server_name.lower()
    if server_name in ["testpypi", "pypitest"]:
        return(r"https://testpypi.python.org/pypi")
    elif server_name in ["pypi", ]:
        return(r"https://pypi.python.org/pypi")


def update_version_number(ctx, update_level='patch'):
    """Update version number

    Returns a semantic_version object"""

    """Find current version"""
    temp_file = Path(ctx.releaser.version).resolve().parent / ("~" + Path(ctx.releaser.version).name)
    with temp_file.open(mode='w') as g:
        with Path(ctx.releaser.version).resolve().open(mode='r') as f:
            for line in f:
                version_matches = bare_version_re.match(line)
                if version_matches:
                    bare_version_str = version_matches.groups(0)[0]
                    if semantic_version.validate(bare_version_str):
                        current_version = Version(bare_version_str)
                        print("{}Current version is {}".format(" "*4, current_version))
                    else:
                        current_version = Version.coerce(bare_version_str)
                        if not text.query_yes_quit("{}I think the version is {}. Use it?".format(" "*4, current_version), default="yes"):
                            exit(colorama.Fore.RED + 'Please set an initial version number to continue')

                    """Determine new version number"""
                    if update_level is 'major':
                        current_version = current_version.next_major()
                    elif update_level is 'minor':
                        current_version = current_version.next_minor()
                    elif update_level is 'patch':
                        current_version = current_version.next_patch()
                    elif update_level is 'prerelease':
                        if not current_version.prerelease:
                            current_version = current_version.next_patch()
                            current_version.prerelease = ('dev', )
                    elif update_level is None:
                        # don't update version
                        pass
                    else:
                        exit(colorama.Fore.RED + 'Cannot update version in {} mode'.format(update_level))

                    print("{}New version is     {}".format(" "*4, current_version))

                    """Update version number"""
                    line = '__version__ = "{}"\n'.format(current_version)
                print(line, file=g, end="")
        #print('', file=g)  # add a blank line at the end of the file
    shutil.copyfile(str(temp_file), str(Path(ctx.releaser.version).resolve()))
    os.remove(str(temp_file))
    return(current_version)


def build_distribution():
    build_status = subprocess.check_call(['python', 'setup.py', 'sdist', 'bdist_egg', 'bdist_wheel'])
    if build_status is not 0:
        exit(colorama.Fore.RED + 'Something broke tyring to package your code...')


def other_dependancies(server, environment):
    """
    Installs things that need to be in place before installing the main package
    """
    print('  ** Other Dependancides, based on server', server, '**')
    server = server.lower()
    # Pillow is not on TestPyPI
    if server is "local":
        pass
    elif server in ["testpypi", "pypitest"]:
        # these are packages not available on the test server, so install them
        # off the regular pypi server
        print("  **Install Pillow**")
        subprocess.call([environment + '\\Scripts\\pip.exe', 'install', 'Pillow'], shell=True)
    elif server in ["pypi"]:
        print("  **Install Pillow**")
        subprocess.call([environment + '\\Scripts\\pip.exe', 'install', 'Pillow'], shell=True)
    else:
        print("  **Nothing more to install**")


def check_local_install(version, ext, server="local"):
    all_files = list(dist_directory().glob('*.{}'.format(ext)))
    the_file = all_files[0]
    for f in all_files[1:]:
        if f.stat().st_mtime > the_file.stat().st_mtime:
            the_file = f

    environment = 'env-{}-{}-{}'.format(version, ext, server)
    if server == "local":
        pass
    else:
        # upload to server
        print("  **Uploading**")
        subprocess.call(['twine', 'upload', str(the_file), '-r', server])

    if (here_directory() / environment).exists():
        shutil.rmtree(environment)  # remove directory if it exists
    subprocess.call(['python', '-m', 'venv', environment])
    if server == "local":
        subprocess.call([environment + '\\Scripts\\pip.exe', 'install', str(the_file), '--no-cache'], shell=True)
    else:
        other_dependancies(server, environment)
        print("  **Install from server**")
        subprocess.call([environment + '\\Scripts\\pip.exe', 'install', '-i', server_url(server), module_name() + "==" + str(version), '--no-cache'], shell=True)
    print("  **Test version of install package**")
    test_version = subprocess.check_output([environment + '\\Scripts\\python.exe', '-c', "exec(\"\"\"import {0}\\nprint({0}.__version__)\\n\"\"\")".format(module_name())], shell=True)
    test_version = test_version.decode('ascii').strip()
    # print(test_version, type(test_version), type(expected_version))
    if (Version(test_version) == version):
        print('{}{} install {} works!{}'.format(colorama.Fore.GREEN, server, ext, colorama.Style.RESET_ALL))
    else:
        exit('{}{} install {} broken{}'.format(colorama.Fore.RED, server, ext, colorama.Style.RESET_ALL))


def check_existance(to_check, name, config_key=None, relative_to=None):
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


@task
def make_release(ctx):
    '''Make and upload the release.'''

    make_release_version = __version__
    colorama.init()
    text.title("Minchin 'Make Release' for Python v{}".format(make_release_version))

    print()
    text.subtitle("Configuration")
    check_existance(ctx.releaser.here, "base dir", "releaser.here")
    here = Path(ctx.releaser.here).resolve()
    check_existance(ctx.releaser.source, "source", "releaser.source", here)
    check_existance(ctx.releaser.test, "test dir", "releaser.test", here)
    check_existance(ctx.releaser.docs, "doc dir", "releaser.doc", here)
    check_existance(ctx.releaser.version, "version file", "releaser.version", here)

    print()
    text.subtitle("Git -- Clean directory?")
    try:
        repo = git.Repo(str(here))
    except git.exc.InvalidGitRepoposityError:
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
    print()
    text.subtitle("Run Tests")
    print()
    text.subtitle("Update Version Number")
    #new_version = update_version_number(ctx)
    print()
    text.subtitle("Add Release to Changelog")
    print()
    text.subtitle("Build Documentation")
    print()
    ans = text.query_yes_quit('All good and ready to go?')
    if ans is False:
        sys.exit(1)

    text.subtitle("Build Distributions")
    build_distribution()

    for server in [
                    "local",
                    "testpypi",
                    "pypi",
                  ]:
        for file_format in ["tar.gz", "whl"]:
            print()
            text.subtitle("Test {} Build {}".format(file_format, server))
            check_local_install(new_version, file_format, server)

    # new_version = update_version_number('prerelease')