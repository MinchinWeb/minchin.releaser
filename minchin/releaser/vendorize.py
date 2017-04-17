import codecs
import os
import re
import shutil
import sys
from pathlib import Path

import colorama
from invoke import task

from .constants import __version__
from .util import check_configuration, check_existence

try:
    from minchin import text
except ImportError:
    from ._vendor import text



def copytree(src, dst, overwrite=False, ignore_list=None, debug=False):
    """
    Copy a tree of files over.

    Ignores a file if it already exists at the destination.
    """
    if ignore_list is None:
        ignore_list = []
    if debug:
        print('copytree {} to {}'.format(src, dst))
    for child in Path(src).iterdir():
        if debug:
            print("  on file {}".format(child))
        if child.name not in ignore_list:
            if child.is_dir():
                new_dir = Path(dst) / child.relative_to(src)
                new_dir.mkdir(exist_ok=True)
                # call recursively
                copytree(child, new_dir, overwrite, ignore_list, debug)
            elif child.is_file():
                new_file = new_dir = Path(dst) / child.relative_to(src)
                if debug:
                    print("    to file {}".format(new_file))
                if new_file.exists():
                    if overwrite:
                        new_file.unlink()
                        shutil.copy2(child, new_file)
                else:
                    shutil.copy2(child, new_file)
        else:
            if debug:
                print("  Skipping copy of {}".format(child))


def read(*parts):
    # intentionally *not* adding an encoding option to open
    return codecs.open(os.path.join(*parts), 'r').read()


def read_requirements(*parts):
    """
    Given a requirements.txt (or similar style file), returns a list of requirements.

    Assumes anything after a single '#' on a line is a comment, and ignores
    empty lines.
    """
    requirements = []
    for line in read(*parts).splitlines():
        new_line = re.sub(r'(\s*)?#.*$',  # the space immediately before the
                                          # hash mark, the hash mark, and
                                          # anything that follows it
                          '',  # replace with a blank string
                          line)
        if new_line:  # i.e. we have a non-zero-length string
            requirements.append(new_line)
    return requirements


@task
def vendorize(ctx, PACKAGES=None, dest_dir=None, internal_call=False):
    """Vendor-ize packages."""
    if not internal_call:
        colorama.init()
        text.title("Minchin Vendorize-er for Python Projects v{}".format(__version__))

        print()

    text.subtitle("Configuration")
    extra_keys = ['here',
                  'source',
                  'module_name',
                  'vendor_dest',
                  'vendor_packages',
                  'vendor_override_src',
                 ]
    if not internal_call:
        check_configuration(ctx, 'releaser', extra_keys)
        check_existence(ctx.releaser.here, "base dir", "releaser.here")
    here = Path(ctx.releaser.here).resolve()

    if not internal_call:
        try:
            check_existence(ctx.releaser.source, "source", "releaser.source", here)
        except FileNotFoundError:
            sys.exit(1)

    check_existence(ctx.releaser.vendor_dest, "vendor dir", "releaser.vendor_dest",
                    here, allow_not_existing=True)
    check_existence(ctx.releaser.vendor_override_src, "override dir",
                    "releaser.vendor_override_src", here, True)
    print()


    dest_dir = Path(ctx.releaser.vendor_dest).resolve()
    base_pkg_dir = Path(ctx.releaser.source)
    # remove and recreate base folder
    text.subtitle("Removing existing vendored directory.")
    try:
        shutil.rmtree(str(dest_dir))
    except FileNotFoundError:
        # directory already deleted
        pass
    dest_dir.mkdir(exist_ok=True)
    print()

    my_req = ['# Requirements for {}'.format(ctx.releaser.module_name),
              '#',
              '# This is built by the minchin.releaser.vendorize script. Do not edit it directly.',
              '',
             ]
    my_req_add = []

    PACKAGES = tuple(ctx.releaser.vendor_packages.keys())

    for package in PACKAGES:
        text.subtitle("Vendorizing {}".format(package))
        req_to_add = []
        # copy python code
        root_dir = (here / ctx.releaser.vendor_packages[package].src).resolve()
        pkg_dest_dir = (dest_dir / ctx.releaser.vendor_packages[package].dest).resolve()
        pkg_dest_dir.mkdir(exist_ok=True)
        print("Copying code from {}".format(root_dir))
        copytree(str(root_dir), str(pkg_dest_dir), True, ['__pycache__'])


        # build requirements file
        try:
            pkg_req_override = (here / ctx.releaser.vendor_packages[package].requirements).resolve()
        except AttributeError:
            pkg_req_override = None
        pkg_req = root_dir / 'requirements.in'
        pkg_req_alt = root_dir / 'requirements.txt'
        if pkg_req_override and pkg_req_override.exists():
            print("  Using project override requirements.")
            req_to_add = read_requirements(str(pkg_req_override))
        elif pkg_req.exists():
            req_to_add = read_requirements(str(pkg_req))
        elif pkg_req_alt.exists():
            print("  Using requirements.TXT.")
            req_to_add = read_requirements(str(pkg_req_alt))
        else:
            print("  No requirements found.")
        my_req_add.extend(req_to_add)
        print()

    text.subtitle("Building requirements-vendor.in")
    # remove vendorized items from requirements list
    my_req_add = [i for i in set(my_req_add) if not i.startswith(PACKAGES)]
    my_req_add.sort()
    my_req.extend(my_req_add)

    # write out requirements file
    dst_req = here / 'requirements-vendor.in'
    dst_req.write_text('\n'.join(my_req) + '\n')
    print()

    # copy over project specific override files
    text.subtitle("Copying over project-specific vendorized overrides.")
    root_dir = Path(ctx.releaser.vendor_override_src)
    copytree(str(root_dir), str(dest_dir), overwrite=True,
             ignore_list=['__pycache__'])
    print()

    if not internal_call:
        text.centered("--- FIN ---")
