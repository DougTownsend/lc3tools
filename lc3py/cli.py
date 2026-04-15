import sys
from .cli_bindings import asm_main, sim_main


def lc3asm():
    # Pass terminal arguments to the C++ run function
    sys.exit(asm_main(sys.argv))

def lc3sim():
    sys.exit(sim_main(sys.argv))

def lc3pysim():
    try:
        from .cli_bindings import curs_main
    except ImportError:
        print("Error: lc3pysim requires Qt to be installed.",
              file=sys.stderr)
        if sys.platform == "darwin":
            print("  Install it with: brew install qt pkg-config", file=sys.stderr)
            print("  Then rebuild:    pip3 install . --no-build-isolation --no-cache-dir", file=sys.stderr)
        elif sys.platform == "win32":
            print("  On Windows, use the MSI installer instead of pip.", file=sys.stderr)
        else:
            print("  Ubuntu/Debian: sudo apt install libqt5widgets5 qtbase5-dev", file=sys.stderr)
            print("  Then rebuild:  pip3 install . --no-build-isolation --no-cache-dir", file=sys.stderr)
        sys.exit(1)
    sys.exit(curs_main(sys.argv, sys.executable))
