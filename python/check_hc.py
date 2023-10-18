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


target = ["x86_64-linux-musl", "i686-linux-musl", "mips-linux-musl", "mipsel-linux-musl", "arm-linux-musleabi", "aarch64-linux-musl", "mips64eb-linux-musl", "mips64el-linux-musl"]

matching = [i for i in target if arch in i]
if not matching:
    if "i386" in arch:
        matching = "i686-linux-musl"
else:
    matching = matching[0]


'''
serve files:
    python -m http.server 8809
collect debug info:
    nc -q 0 -l -p 8889 | tar -xv
'''

debug = False
host = "18.4.85.124"
host_serve_port = 8888
host_debug_port = 8889


@panda.queue_blocking
def run_cmd():
    panda.revert_sync("root")
    target = f"hc_test-{matching}"

    # networking fails on x86_64 target without dhclient
    if arch == "x86_64":
        print(panda.run_serial_cmd("dhclient"))
    
    # if we're seriously debugging let's get core dumps
    if debug:
        print(panda.run_serial_cmd("ulimit -c unlimited"))
        print(panda.run_serial_cmd("sudo sysctl -w kernel.core_pattern=/tmp/core"))

    print(panda.run_serial_cmd(f"wget http://{host}:{host_serve_port}/{target}"))
    panda.run_serial_cmd(f"chmod +x {target}")
    print(panda.run_serial_cmd(f"./{target}"))
    
    # if we're seriously debugging let's send core dumps back to the host
    if debug:
        print(panda.run_serial_cmd(f"tar -cvf - /tmp/core | nc {host} {host_debug_port}"))
    panda.end_analysis()

'''
This is the real test for the system. We should see an output of 0x1000,
a string of "Hello, world!", and a length of 13.
'''
MAGIC_VAL = 5
ERROR_VAL = 0x12345678
EXPECTED_MESSAGE = "hello world!"
success = False


@panda.cb_guest_hypercall
def hypercall(cpu):
    magic, cmd, argsptr, numargs = panda.arch.get_args(cpu, 4, convention="syscall")
    if magic != MAGIC_VAL:
        print(f"Found hypercall, but value was {magic}")
        return False
    if cmd != 1:
        print(f"Got unexpected command")
        return False
    args_ptr = panda.virtual_memory_read(cpu, argsptr, int(numargs*(panda.bits/8)), fmt="ptrlist")
    msg_ptr = args_ptr[0]
    msg_len = panda.virtual_memory_read(cpu, args_ptr[1], 4, fmt="int")
    try:
        msg = panda.virtual_memory_read(cpu, msg_ptr, msg_len)
    except ValueError:
        msg = "?"
    print(f"Got message: {msg}")
    if EXPECTED_MESSAGE in msg.decode():
        global success
        success = True
    panda.arch.set_retval(cpu, 0x1000, convention="syscall")
    return True

panda.run()
if success:
    print("[green]Success![/green]")
else:
    print("[red]Failure![/red]")