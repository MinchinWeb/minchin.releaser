# -*- coding: UTF-8 -*-

from .constants import (
    __author__,
    __description__,
    __email__,
    __license__,
    __title__,
    __url__,
    __version__,
)

try:
    from .make_release import make_release
except ImportError:
    pass
from .vendorize import vendorize
