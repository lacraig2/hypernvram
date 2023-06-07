#!/usr/bin/env python3
'''
Test the hypercall interface
'''
from sys import argv
from pandare import Panda
from rich import print

# Single arg of arch, defaults to i386
arch = "arm" if len(argv) <= 1 else argv[1]
panda = Panda(generic=arch)


target = ["x86_64-unknown-linux-musl", "i686-unknown-linux-musl", "mips-unknown-linux-musl", "mipsel-unknown-linux-musl", "arm-unknown-linux-musleabi", "aarch64-unknown-linux-musl", "mips64-unknown-linux-muslabi64", "mips64el-unknown-linux-muslabi64"]

matching = [i for i in target if arch in i]
if not matching:
    if "i386" in arch:
        matching = "i686-unknown-linux-musl"
else:
    matching = matching[0]


'''
serve files:
    python -m http.server 8809
collect debug info:
    nc -q 0 -l -p 8889 | tar -xv
'''

debug = True
host = "18.4.85.151"
host_serve_port = 8809
host_debug_port = 8889


@panda.queue_blocking
def run_cmd():
    panda.revert_sync("root")
    target = f"{matching}"

    # networking fails on x86_64 target without dhclient
    if arch == "x86_64":
        print(panda.run_serial_cmd("dhclient"))
    
    # if we're seriously debugging let's get core dumps
    if debug:
        print(panda.run_serial_cmd("ulimit -c unlimited"))
        print(panda.run_serial_cmd("sudo sysctl -w kernel.core_pattern=/tmp/core"))

    cli = f"cli_example-{target}"
    print(panda.run_serial_cmd(f"wget http://{host}:{host_serve_port}/ld-musl-i386.so.1 "))

    print(panda.run_serial_cmd(f"wget http://{host}:{host_serve_port}/{target}/{cli}"))
    print(panda.run_serial_cmd(f"wget http://{host}:{host_serve_port}/{target}/libnvram-{target}.so"))
    print(panda.run_serial_cmd(f"chmod 777 ld-musl-i386.so.1 "))
    print(panda.run_serial_cmd(f"cp ld-musl-i386.so.1  /lib/"))
    print(panda.run_serial_cmd(f"chmod +x {cli}"))
    print(panda.run_serial_cmd(f"chmod +x libnvram-{target}.so"))
    print(panda.run_serial_cmd(f"file ./{cli}"))
    print(panda.run_serial_cmd(f"ls -la /lib"))
    print(panda.run_serial_cmd(f"bash -c 'LD_LIBRARY_PATH=$PWD ./{cli}'"))
    
    # if we're seriously debugging let's send core dumps back to the host
    if debug:
        print(panda.run_serial_cmd(f"tar -cvf - /tmp/core | nc {host} {host_debug_port}"))
    panda.end_analysis()

'''
This is the real test for the system. We should see an output of 0x1000,
a string of "Hello, world!", and a length of 13.
'''
MAGIC_VAL = 0x31838188
ERROR_VAL = 0x12345678


@panda.cb_guest_hypercall
def hypercall(cpu):
    if panda.arch.get_arg(cpu, 0, convention="syscall") != MAGIC_VAL:
        if debug:
            print(f"Found hypercall, but value was {hex(panda.arch.get_arg(cpu, 0, convention='syscall'))}")
        return False
    if panda.arch.get_retval(cpu, convention="syscall") != MAGIC_VAL:
        print(f"ERROR VALUE FAILING {hex(panda.arch.get_retval(cpu, convention='syscall'))}")
    print(f"len {panda.arch.get_arg(cpu, 1, convention='syscall')}")
    print(f"got output '{panda.read_str(cpu, panda.arch.get_arg(cpu, 2, convention='syscall')).strip()}'")
    panda.arch.set_retval(cpu, 0x1000, convention="syscall")
    return True

panda.run()
