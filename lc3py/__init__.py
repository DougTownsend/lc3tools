from .core import Simulator as _Simulator, Assembler, Printer, Inputter
import time


class Simulator:

    def __init__(self, rand=False):
        self.input = Inputter()
        self.output = Printer()
        self.asm = Assembler(self.output, 4)
        self.sim = _Simulator(self.output, self.input, 1)
        self._symbols = {}   # accumulated label → address from assemble()
        if rand:
            self.randomize()

    def read(self):
        return self.output.read()

    def print(self):
        print(self.read())
    
    def write(self, str):
        self.input.set_input(str)
    
    def assemble(self, asmfile, ret_symtab=False):
        asm = self.asm.assemble(asmfile)
        if asm is None:
            return None
        # Store symbols so exec_jsr() can look up labels
        self._symbols.update(asm[1])
        if ret_symtab:
            return asm
        return asm[0]

    def load_obj(self, objfile):
        return self.sim.load_object_file(objfile)

    def run(self):
        return self.sim.run()
    
    def step_in(self):
        return self.sim.step_in()
    
    def step_over(self):
        return self.sim.step_over()
    
    def read_mem(self, addr):
        return self.sim.read_mem(addr)

    def write_mem(self, addr, value):
        self.sim.write_mem(addr, value)
    
    def read_mem_line(self, addr):
        return self.sim.read_mem_line(addr)

    def read_reg(self, reg):
        return self.sim.read_reg(reg)

    def write_reg(self, reg, value):
        self.sim.write_reg(reg, value)

    def read_psr(self):
        return self.sim.read_psr()

    def get_pc(self):
        return self.sim.get_pc()
    
    def set_pc(self, value):
        self.sim.set_pc(value)
    
    def set_inst_limit(self, value):
        self.sim.set_inst_limit(value)

    def exceeded_inst_limit(self):
        return self.sim.exceeded_inst_limit()
    
    def randomize(self):
        return self.sim.randomize(int(time.time()))

    def reinit(self):
        return self.sim.reinit()

    def run_until_halt_or_input(self, inst_limit=0):
        """Run until PC points to HALT or GETC.
        Returns True if stopped at GETC, False if stopped at HALT.
        If already at HALT, does nothing. If already at GETC, steps past
        it and runs to the next HALT or GETC."""
        return self.sim.run_until_halt_or_input(inst_limit)

    def exec_jsr(self, target, inst_limit=1000000):
        """Execute a subroutine as if JSR had been called to it.

        target: either a label string (e.g. "draw") or an integer address.
                Labels are looked up in symbols from prior assemble() calls.
        inst_limit: safety cap on instructions (default 1M) to avoid
                    hanging on infinite loops.

        Sets R7 to a sentinel address, sets PC to the subroutine, and runs
        until the subroutine's RET jumps back to the sentinel. Useful for
        autograder tests that set up registers/memory, invoke a student
        subroutine, and then inspect the effects.

        Returns True if the subroutine returned normally, False if the
        instruction limit was hit (likely infinite loop or missing RET).
        """
        if isinstance(target, str):
            # Labels are case-insensitive in LC-3 assembly
            key = target.lower()
            match = {k.lower(): v for k, v in self._symbols.items()}.get(key)
            if match is None:
                raise KeyError(f"Label {target!r} not found. Assemble the "
                               f"source file first with sim.assemble(...).")
            addr = match
        else:
            addr = int(target)

        # Sentinel: the interrupt vector at 0x0000. Not executed in normal
        # user code, so a breakpoint here is safe.
        SENTINEL = 0x0000

        self.sim.write_reg(7, SENTINEL)
        self.sim.set_pc(addr)
        self.sim.set_breakpoint(SENTINEL)
        self.sim.set_inst_limit(inst_limit)
        self.sim.run()
        self.sim.remove_breakpoint(SENTINEL)

        return not self.sim.exceeded_inst_limit()