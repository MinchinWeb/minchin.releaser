import os
import re
import shutil
import sys
import textwrap
from pathlib import Path

import colorama
import git  # packaged as 'gitpython'
import invoke
import isort
import semantic_version
from invoke import task
from semantic_version import Version

# try:
#     from minchin import text
# except ImportError:
#     from ._vendor import text
from ._vendor import text
from .constants import (
    ERROR_COLOR,
    GOOD_COLOR,
    PIP_EXT,
    RESET_COLOR,
    VENV_BIN,
    WARNING_COLOR,
    __version__,
)
from .util import check_configuration, check_existence
from .vendorize import vendorize

# also requires `twine`

# assumed Invoke configuration file points to Windows Shell

version_re = re.compile(
    r"__version__ = [\"\']{1,3}(?P<major>\d+)\.(?P<minor>\d+).(?P<patch>\d+)(?:-(?P<prerelease>[0-9A-Za-z\.]+))?(?:\+[0-9A-Za-z-\.]+)?[\"\']{1,3}"
)
bare_version_re = re.compile(r"__version__ = [\"\']{1,3}([\.\dA-Za-z+-]*)[\"\']{1,3}")
list_match_re = re.compile(r"(?P<leading>[ \t]*)(?P<mark>[-\*+]) +:\w+:")


VALID_BUMPS = [
    # none
    "none",
    # dev
    "prerelease",
    "dev",
    "development",
    # bugfix
    "patch",
    "bugfix",
    # feature
    "minor",
    "feature",
    # major/breaking changes
    "major",
    "breaking",
]
VALID_BUMPS_STR = ", & ".join([", ".join(VALID_BUMPS[:-1]), VALID_BUMPS[-1]])


def server_url(server_name, download=False):
    """Determine the server URL to download packages from."""
    server_name = server_name.lower()
    if server_name in ["testpypi", "pypitest"]:
        if download:
            return r"https://test.pypi.org/simple"
        else:
            return r"https://test.pypi.org/legacy/"
    elif server_name in [
        "pypi",
    ]:
        return r"https://pypi.org/pypi"


def update_version_number(ctx, bump=None, ignore_prerelease=False):
    """
    Update version number.

    Args
    ----
        bump (str): bump level
        ignore_prerelease (bool): ignore the fact that our new version is a
            prerelease, or issue a warning

    Returns
    -------
        a two semantic_version objects (the old version and the current
        version).

    """
    if bump is not None and bump.lower() not in VALID_BUMPS:
        print(
            textwrap.fill(
                "[{}WARN{}] bump level, as provided on command "
                "line, is invalid. Trying value given in "
                "configuration file. Valid values are {}.".format(
                    WARNING_COLOR, RESET_COLOR, VALID_BUMPS_STR
                ),
                width=text.get_terminal_size().columns - 1,
                subsequent_indent=" " * 7,
            )
        )
        bump = None
    else:
        update_level = bump

    # Find current version
    temp_file = Path(ctx.releaser.version).resolve().parent / (
        "~" + Path(ctx.releaser.version).name
    )
    with temp_file.open(mode="w", encoding="utf-8") as g:
        with Path(ctx.releaser.version).resolve().open(mode="r", encoding="utf-8") as f:
            for line in f:
                version_matches = bare_version_re.match(line)
                if version_matches:
                    bare_version_str = version_matches.groups(0)[0]
                    if semantic_version.validate(bare_version_str):
                        old_version = Version(bare_version_str)
                        print("{}Current version is {}".format(" " * 4, old_version))
                    else:
                        old_version = Version.coerce(bare_version_str)
                        ans = text.query_yes_quit(
                            "{}I think the version is {}."
                            " Use it?".format(" " * 4, old_version),
                            default="yes",
                        )
                        if ans == text.Answers.QUIT:
                            exit(
                                "[{}ERROR{}] Please set an initial version "
                                "number to continue.".format(ERROR_COLOR, RESET_COLOR)
                            )

                    # if bump level not defined by command line options
                    if bump is None:
                        try:
                            update_level = ctx.releaser.version_bump
                        except AttributeError:
                            print(
                                "[{}WARN{}] bump level not defined in "
                                "configuration. Use key "
                                "'releaser.version_bump'".format(
                                    WARNING_COLOR, RESET_COLOR
                                )
                            )
                            print(
                                textwrap.fill(
                                    "{}Valid bump levels are: "
                                    "{}. Or use 'quit' to exit.".format(
                                        " " * 7, VALID_BUMPS_STR
                                    ),
                                    width=text.get_terminal_size().columns - 1,
                                    subsequent_indent=" " * 7,
                                )
                            )
                            my_input = input("What bump level to use? ")
                            if my_input.lower() in ["quit", "q", "exit", "y"]:
                                sys.exit(0)
                            elif my_input.lower() not in VALID_BUMPS:
                                exit(
                                    "[{}ERROR{}] invalid bump level provided. "
                                    "Exiting...".format(ERROR_COLOR, RESET_COLOR)
                                )
                            else:
                                update_level = my_input

                    # Determine new version number
                    if update_level is None or update_level.lower() in ["none"]:
                        update_level = None
                    elif update_level is not None:
                        update_level = update_level.lower()

                    if update_level in ["breaking", "major"]:
                        current_version = old_version.next_major()
                    elif update_level in ["feature", "minor"]:
                        current_version = old_version.next_minor()
                    elif update_level in ["bugfix", "patch"]:
                        current_version = old_version.next_patch()
                    elif update_level in ["dev", "development", "prerelease"]:
                        if not old_version.prerelease:
                            current_version = old_version.next_patch()
                            current_version.prerelease = ("dev",)
                        else:
                            current_version = old_version
                    elif update_level is None:
                        # don't update version
                        current_version = old_version
                    else:
                        exit(
                            "[{}ERROR{}] Cannot update version in {} mode".format(
                                ERROR_COLOR, RESET_COLOR, update_level
                            )
                        )

                    # warn on pre-release versions
                    if current_version.prerelease and not ignore_prerelease:
                        ans = text.query_yes_quit(
                            "[{}WARN{}] Current version "
                            "is a pre-release version. "
                            "Continue anyway?".format(WARNING_COLOR, RESET_COLOR),
                            default="quit",
                        )
                        if ans == text.Answers.QUIT:
                            sys.exit(1)

                    print("{}New version is     {}".format(" " * 4, current_version))

                    # Update version number
                    line = '__version__ = "{}"\n'.format(current_version)
                print(line, file=g, end="")
        # print('', file=g)  # add a blank line at the end of the file
    shutil.copyfile(str(temp_file), str(Path(ctx.releaser.version).resolve()))
    os.remove(str(temp_file))
    return (old_version, current_version)


def build_distribution():
    """Build distributions of the code."""
    result = invoke.run(
        "python setup.py sdist bdist_egg bdist_wheel", warn=True, hide=True
    )
    if result.ok:
        print(
            "[{}GOOD{}] Distribution built without errors.".format(
                GOOD_COLOR, RESET_COLOR
            )
        )
    else:
        print(
            "[{}ERROR{}] Something broke trying to package your "
            "code...".format(ERROR_COLOR, RESET_COLOR)
        )
        print(result.stderr)
        sys.exit(1)


def other_dependencies(ctx, server, environment):
    """Install things that need to be in place before installing the main package."""
    if "extra_packages" in ctx.releaser:
        server = server.lower()
        extra_pkgs = []
        if server in ["local"]:
            if "local" in ctx.releaser.extra_packages:
                extra_pkgs.extend(ctx.releaser.extra_packages.local)
        elif server in ["testpypi", "pypitest"]:
            # these are packages not available on the test server, so install them
            # off the regular pypi server
            if (
                "test" in ctx.releaser.extra_packages
                and ctx.releaser.extra_packages.test is not None
            ):
                extra_pkgs.extend(ctx.releaser.extra_packages.test)
        elif server in ["pypi"]:
            if (
                "pypi" in ctx.releaser.extra_packages
                and ctx.releaser.extra_packages.pypi is not None
            ):
                extra_pkgs.extend(ctx.releaser.extra_packages.pypi)
        else:
            print("** Nothing more to install **")

        if extra_pkgs:
            print("** Other Dependencies, based on server", server, "**")

        for pkg in extra_pkgs:
            result = invoke.run(
                ".{0}env{0}{1}{0}{2}{0}pip{3} install {4}".format(
                    os.sep, environment, VENV_BIN, PIP_EXT, pkg
                ),
                hide=True,
            )
            if result.ok:
                print(
                    "{}[{}GOOD{}] Installed {}".format("", GOOD_COLOR, RESET_COLOR, pkg)
                )
            else:
                print(
                    "{}[{}ERROR{}] Something broke trying to install "
                    "package: {}".format("", ERROR_COLOR, RESET_COLOR, pkg)
                )
                print(result.stderr)
                sys.exit(1)


def check_local_install(ctx, version, ext, server="local"):
    """
    Upload and check if install works.

    Uploads a distribution to PyPI, and then tests to see if I can download and
    install it.

    Returns
    -------
        str: string summazing operation

    """
    here = Path(ctx.releaser.here).resolve()
    dist_dir = here / "dist"

    all_files = list(dist_dir.glob("*.{}".format(ext)))
    the_file = all_files[0]
    for f in all_files[1:]:
        if f.stat().st_mtime > the_file.stat().st_mtime:
            the_file = f
            # this is the latest generated file of the given version

    environment = "env-{}-{}-{}".format(version, ext, server)
    if server == "local":
        pass
    else:
        # upload to server
        print("** Uploading to server **")
        cmd = "twine upload {}".format(the_file)
        # for PyPI, let twine pick the server
        if server != "pypi":
            cmd = cmd + " -r {}".format(server)
        result = invoke.run(cmd, warn=True)
        if result.failed:
            print(
                textwrap.fill(
                    "[{}ERROR{}] Something broke trying to upload "
                    "your package. This will be the case if you "
                    "have already uploaded it before. To upload "
                    "again, use a different version number "
                    "(or a different build by including a '+' "
                    "suffix to your version number).".format(ERROR_COLOR, RESET_COLOR),
                    width=text.get_terminal_size().columns - 1,
                    subsequent_indent=" " * 8,
                )
            )
            # print(result.stderr)

    # remove directory if it exists
    if (here / "env" / environment).exists():
        shutil.rmtree("env" + os.sep + environment)
    invoke.run("python -m venv env{}{}".format(os.sep, environment))
    other_dependencies(ctx, server, environment)
    if server == "local":
        result = invoke.run(
            ".{0}env{0}{1}{0}{2}{0}pip{3} install {4} --no-cache".format(
                os.sep, environment, VENV_BIN, PIP_EXT, the_file
            ),
            hide=True,
        )
    else:
        # print("  **Install from server**")
        result = invoke.run(
            ".{0}env{0}{1}{0}{2}{0}pip{3} install -i {4} "
            "{5}=={6} --no-cache".format(
                os.sep,
                environment,
                VENV_BIN,
                PIP_EXT,
                server_url(server, download=True),
                ctx.releaser.module_name,
                version,
            ),
            hide=True,
        )
        if result.failed:
            print(
                "[{}ERROR{}] Something broke trying to install your package.".format(
                    ERROR_COLOR, RESET_COLOR
                )
            )
            print(result.stderr)
            sys.exit(1)
    print("** Test version of installed package **")

    result = invoke.run(
        ".{0}env{0}{1}{0}{2}{0}python{3} -c "
        "'exec(\\\"\\\"\\\"import {4}\\nprint({4}.__version__)\\\"\\\"\\\")'".format(
            os.sep, environment, VENV_BIN, PIP_EXT, (ctx.releaser.module_name).strip()
        )
    )
    test_version = result.stdout.strip()
    # print(test_version, type(test_version), type(expected_version))
    if Version(test_version) == version:
        results = "{}{} install {} works!{}".format(
            GOOD_COLOR, server, ext, RESET_COLOR
        )
    else:
        results = "{}{} install {} broken{}".format(
            ERROR_COLOR, server, ext, RESET_COLOR
        )
    print(results)
    return results


@task(
    optional=["bump", "skip-isort", "skip-local", "skip-test", "skip-pypi"],
    help={
        "bump": "What level to bump the version by. Setting this "
        "overrides the value set in your configuration. "
        "Valid bump levels are {}.".format(VALID_BUMPS_STR),
        "skip-isort": "Skip applying isort to your files.",
        "skip-local": "Skip testing by installing from local build " "distribution.",
        "skip-test": "Skip testing by uploading and installing to test " "PyPI server.",
        "skip-pypi": "Skip testing by uploading and installing to (the "
        "real) PyPI server.",
    },
)
def make_release(
    ctx, bump=None, skip_local=False, skip_test=False, skip_pypi=False, skip_isort=False
):
    """Make and upload the release."""
    colorama.init()
    text.title("Minchin 'Make Release' for Python Projects v{}".format(__version__))
    print()

    text.subtitle("Configuration")
    extra_keys = [
        "here",
        "source",
        "test",
        "docs",
        "version",
        "module_name",
    ]
    check_configuration(ctx, "releaser", extra_keys)

    check_existence(ctx.releaser.here, "base dir", "releaser.here")

    here = Path(ctx.releaser.here).resolve()
    try:
        check_existence(ctx.releaser.source, "source", "releaser.source", here)
        check_existence(ctx.releaser.test, "test dir", "releaser.test", here, True)
        check_existence(ctx.releaser.docs, "doc dir", "releaser.docs", here, True)
        check_existence(ctx.releaser.version, "version file", "releaser.version", here)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
    print()

    text.subtitle("Git -- Clean directory?")
    try:
        repo = git.Repo(str(here))
    except git.exc.InvalidGitRepositoryError:
        repo = None
        print(
            textwrap.fill(
                "[{}WARN{}] base directory does not appear to be "
                "a valid git repo.".format(WARNING_COLOR, RESET_COLOR),
                width=text.get_terminal_size().columns - 1,
                subsequent_indent=" " * 7,
            )
        )

    if repo is not None:
        if repo.is_dirty():
            print(
                textwrap.fill(
                    "[{}WARN{}] git repo is dirty. You should "
                    "probably commit your changes before "
                    "continuing.".format(WARNING_COLOR, RESET_COLOR),
                    width=text.get_terminal_size().columns - 1,
                    subsequent_indent=" " * 7,
                )
            )
            # True = yes, False = Quit
            ans = text.query_yes_quit(
                " " * 7 + "Continue anyway or quit?", default="quit"
            )
            if ans == text.Answers.QUIT:
                sys.exit(1)
        else:
            print("[{}GOOD{}] Clean Git repo.".format(GOOD_COLOR, RESET_COLOR))
    print()

    text.subtitle("Sort Import Statements")
    if not skip_isort:
        for f in Path(ctx.releaser.source).resolve().glob("**/*.py"):
            isort.file(f)
            print(".", end="")
        if ctx.releaser.test is not None:
            for f in Path(ctx.releaser.test).resolve().glob("**/*.py"):
                isort.file(f)
                print(".", end="")
        print(" Done!")
    else:
        print("[{}WARN{}] Skipped!".format(WARNING_COLOR, RESET_COLOR))
    print()

    if "vendor_packages" in ctx.releaser.keys():
        text.subtitle("Vendorize!")
        vendorize(ctx, internal_call=True)

    text.subtitle("Run Tests")
    # check setup.py
    # python setup.py -r -s
    # https://stackoverflow.com/questions/30328259/what-does-python-setup-py-check-actually-do
    try:
        cmd_none = (ctx.releaser.test_command).lower()
    except AttributeError:
        print(
            "[{}WARN{}] test command not configured. Use key "
            "'releaser.test_command'.".format(WARNING_COLOR, RESET_COLOR)
        )
        cmd_none = "none"
    if cmd_none != "none":
        result = invoke.run(ctx.releaser.test_command, warn=True)
        if not result.ok:
            print(
                "[{}WARN{}] the test suite reported errors.".format(
                    WARNING_COLOR, RESET_COLOR
                )
            )
            ans = text.query_yes_quit(
                " " * 7 + "Continue anyway or quit?", default="quit"
            )
            if ans == text.Answers.QUIT:
                sys.exit(1)
    else:
        print("[{}WARN{}] No test command given.".format(WARNING_COLOR, RESET_COLOR))
    print()

    text.subtitle("Update Version Number")
    old_version, new_version = update_version_number(ctx, bump)
    print()

    text.subtitle("Add Release to Changelog")
    if old_version == new_version:
        print(
            "[{}WARN{}] Version hasn't changed. Not updating Changelog.".format(
                WARNING_COLOR, RESET_COLOR
            )
        )
    else:
        print(
            "[{}WARN{}] I can't do this yet, but you probably should.\n"
            "           Not updating Changelog.".format(WARNING_COLOR, RESET_COLOR)
        )
        # https://github.com/bitprophet/releases/blob/master/releases/util.py#L21
        # https://github.com/pyinvoke/invocations/blob/master/invocations/packaging/release.py#L362
    print()

    text.subtitle("Build Documentation")
    try:
        cmd_none = (ctx.releaser.doc_command).lower()
    except (AttributeError, KeyError):
        print(
            "[{}WARN{}] documentation generation command not configured.\n"
            "           Use key 'releaser.doc_command'.".format(
                WARNING_COLOR, RESET_COLOR
            )
        )
        cmd_none = "none"
    if cmd_none != "none":
        result = invoke.run(ctx.releaser.doc_command, warn=True)
        if not result.ok:
            print(
                "[{}WARN{}] the documentation generation reported errors.".format(
                    WARNING_COLOR, RESET_COLOR
                )
            )
            ans = text.query_yes_quit(
                " " * 7 + "Continue anyway or quit?", default="quit"
            )
            if ans == text.Answers.QUIT:
                sys.exit(1)
    else:
        print(
            "[{}WARN{}] No docmentation generation command given.".format(
                WARNING_COLOR, RESET_COLOR
            )
        )
    print()

    ans = text.query_yes_quit("All good and ready to go?")
    if ans == text.Answers.QUIT:
        sys.exit(1)
    print()

    text.subtitle("Build Distributions")
    build_distribution()
    print()

    text.subtitle("Check Readme Rendering")
    result = invoke.run("twine check dist/*", warn=True)
    if not result.ok:
        print(
            "[{}WARN{}] Readme reported ReST rendering errors.".format(
                WARNING_COLOR, RESET_COLOR
            )
        )
        ans = text.query_yes_quit(" " * 7 + "Continue anyway or quit?", default="quit")
        if ans == text.Answers.QUIT:
            sys.exit(1)
    else:
        print("[{}GOOD{}] Readme renders.".format(GOOD_COLOR, RESET_COLOR))
    print()

    server_list = []
    if not skip_local:
        server_list.append("local")
    if not skip_test:
        server_list.append("testpypi")
    if not skip_pypi:
        server_list.append("pypi")

    success_list = []
    for server in server_list:
        for file_format in ["tar.gz", "whl"]:
            text.subtitle("Test {} Build {}".format(file_format, server))
            s = check_local_install(ctx, new_version, file_format, server)
            success_list.append(s)
            print()

    text.subtitle("Install Test Summary")
    for line in success_list:
        print(line)
    print()

    # git commit

    if repo is not None:
        text.subtitle("Create Git Tag")
        _create_tag = True

        # don't duplicate existing tag
        tags = repo.tags
        for tag in tags:
            if tag.name == new_version:
                print(
                    "[{}WARN{}] Git tag for version {} already exists. "
                    "Skipping.".format(WARNING_COLOR, RESET_COLOR, tag.name)
                )
                _create_tag = False
                break

        # warn on pre-release versions
        if new_version.prerelease:
            print(
                "[{}WARN{}] Currently a pre-release version.".format(
                    WARNING_COLOR, RESET_COLOR
                )
            )
            # True = yes, False = Quit
            ans = text.query_yes_no(" " * 7 + "Create Git tag anyway?", default="no")
            if ans == text.Answers.NO:
                _create_tag = False
        else:
            ans = text.query_yes_no(
                "Create Git tag for version {}?".format(new_version), default="no"
            )
            if ans == text.Answers.NO:
                _create_tag = False

        if _create_tag:
            print("Creating Git tag for version {}".format(new_version))
            repo.create_tag(new_version)
        print()

    text.subtitle("Bump Version to Pre-release?")
    ans = text.query_yes_no("Bump version to pre-release now?")
    if ans == text.Answers.YES:
        old_version, new_version = update_version_number(ctx, "prerelease", True)
