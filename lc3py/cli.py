import sys
from .cli_bindings import asm_main, sim_main
#from .core import sim_backend

def lc3asm():
    # Pass terminal arguments to the C++ run function
    sys.exit(asm_main(sys.argv))

def lc3sim():
    sys.exit(sim_main(sys.argv))
