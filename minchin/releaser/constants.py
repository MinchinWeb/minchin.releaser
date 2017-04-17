import colorama

__title__ = "minchin.releaser"
__version__ = "0.4.0"
__description__ = "Minchin.Releaser is a collection of tools designed to make releasing Python packages easier."
__author__ = "William Minchin"
__email__ = "w_minchin@hotmail.com"
__url__ = "https://github.com/MinchinWeb/minchin.releaser"
__license__ = "MIT License"


ERROR_COLOR = colorama.Fore.RED
WARNING_COLOR = colorama.Fore.YELLOW
GOOD_COLOR = colorama.Fore.GREEN
RESET_COLOR = colorama.Style.RESET_ALL

# on Windows, this should be '.exe', but we get away with setting it to
# blank as Windows will (typically) run .exe files without specifying the
# file extension
PIP_EXT = ''
