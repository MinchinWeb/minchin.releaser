# task.py file for invoke

try:
    from minchin.releaser import make_release
except ImportError:
    print("[WARN] Run 'vendorize' to bootstrap and gain access to 'make_release'")

try:
    from minchin.releaser import vendorize
except ImportError:
    print("[WARN] Install 'minchin.text' to bootstrap")
