import os
from pathlib import Path

from .constants import ERROR_COLOR, RESET_COLOR, WARNING_COLOR


def check_configuration(ctx, base_key, needed_keys):
    """
    Confrim a valid configuration.

    Args:
        ctx (invoke.context):
        base_key (str): the base configuration key everything is under.
        needed_keys (list): sub-keys of the base key that are checked to make
            sure they exist.
    """

    # check for valid configuration
    if base_key not in ctx.keys():
        exit(
            "[{}ERROR{}] missing configuration for '{}'".format(
                ERROR_COLOR, RESET_COLOR, base_key
            )
        )
        # TODO: offer to create configuration file
    if ctx.releaser is None:
        exit(
            "[{}ERROR{}] empty configuration for '{}' found".format(
                ERROR_COLOR, RESET_COLOR, base_key
            )
        )
        # TODO: offer to create configuration file

    # TODO: allow use of default values
    for my_key in needed_keys:
        if my_key not in ctx[base_key].keys():
            exit(
                "[{}ERROR{}] missing configuration key '{}.{}'".format(
                    ERROR_COLOR, RESET_COLOR, base_key, my_key
                )
            )


def check_existence(
    to_check,
    display_name,
    config_key=None,
    relative_to=None,
    allow_undefined=False,
    allow_not_existing=False,
    base_key="releaser",
):
    """
    Determine whether a file or folder actually exists.

    Args:
        to_check (str):
        display_name (str):
        config_key (str):
        relative_to=None:
        allow_undefined (bool):
        allow_not_existing (bool):
        base_key (str):
    """
    if allow_undefined and (to_check is None or to_check.lower() == "none"):
        print("{: <14} -> {}UNDEFINED{}".format(display_name, WARNING_COLOR, RESET_COLOR))
        return
    else:
        if config_key is None:
            config_key = "{}.{}".format(base_key, display_name)
        my_check = Path(to_check).resolve()
        if my_check.exists() and relative_to is not None:
            printed_path = str(my_check.relative_to(relative_to))
            if printed_path != ".":
                printed_path = "." + os.sep + printed_path
        else:
            printed_path = str(my_check)
        if my_check.exists() or allow_not_existing:
            print("{: <14} -> {}".format(display_name, printed_path))
            return
        else:
            raise FileNotFoundError(
                "[{}ERROR{}] '{}', as given, doesn't "
                "exist. For configuration key '{}', was "
                "given: {}".format(ERROR_COLOR, RESET_COLOR, display_name, config_key, to_check)
            )
