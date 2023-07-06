
from pandare import PyPlugin, Panda
import ipaddress
import socket
import os
'''
Interface to LibNvram Hypercalls.

Register callbacks via 
panda.pyplugins.ppp.NVramHC.ppp_reg_cb("NVRAM_GET",get_ipdb_call)
For NVRAM_GET exmaple
TODO: Setup actual list add. Handle additional nvram hooks
'''
class NVramHC(PyPlugin):
    def __init__(self, panda: Panda):
        print("Loading Nvram HyperCall plugin")
        super().__init__(panda)
        self.panda = panda
        outdir = self.get_arg("outdir")
        self.write_file = os.path.join(outdir,"nvram.log")
        open(self.write_file, "w").close() #Clear the file
        self.write2_file = os.path.join(outdir,"nvram2.log")
        open(self.write2_file, "w").close() #Clear the file
        self.nvram:dict = self.get_arg("nvram")
        if self.nvram is None:
            self.nvram = {}
        self.create_callbacks()
        self.MAGIC_VAL = 0x31838188
        self.ERROR_VAL = 0x12345678
        self.conf = 0
        @panda.cb_guest_hypercall
        def hypercall(cpu):
            if panda.arch.get_arg(cpu, 0, convention="syscall") != self.MAGIC_VAL:
                print(f"Found hypercall, but value was {hex(panda.arch.get_arg(cpu, 0, convention='syscall'))}")
                return False
            len = panda.arch.get_arg(cpu, 1, convention='syscall')
            pointer_size = panda.bits //8
            argptr =  panda.arch.get_arg(cpu, 2, convention='syscall')
            argstr = []

            for x in range(0,len):
                addr = int.from_bytes(panda.virtual_memory_read(cpu, argptr + ( pointer_size * x), pointer_size),'little')
                argstr.append(panda.read_str(cpu, addr))
            #print(argstr)
            with open(self.write2_file, "a") as f:
                f.write(f"\n{argstr}\n")
            block = self.ppp_run_cb("NVRAM_BLOCK_ON_ALL",cpu,argstr)
            if block:
                return True
            output = argstr[0]
            if "NVRAM_GET_INT" in output:
                self.get_int(cpu,argstr)
            elif "NVRAM_GET_BUF" in output:
                self.get_buf(cpu,argstr)
            elif "NVRAM_SET_INT" in output:
                self.set_int(cpu,argstr)
            elif "NVRAM_UNSET" in output:
                self.unset(cpu,argstr)
            elif "NVRAM_SET" in output:
                self.set(cpu,argstr)
            elif "NVRAM_LIST_ADD" in output:
                if not self.ppp_run_cb("NVRAM_LIST_ADD"):
                    self.set(cpu,argstr)
            elif "NVRAM_CLEAR" in output:
                self.nvram.clear()
            elif "NVRAM_GETALL" in output:
                self.getall(cpu,argstr)
            elif "INIT" in output:
                if not self.ppp_run_cb("NVRAM_INIT"):
                    self.panda.arch.set_retval(cpu,self.conf)
            else:
                print(argstr)
            return True
    '''
    creates a copy of current nvram dictionary 
    '''
    @PyPlugin.ppp_export
    def get_nvram(self):
        self.nvram.copy()
    @PyPlugin.ppp_export
    def add_nvram(self, key,val):
        self.nvram[key] = val.encode() + b'\0'
    '''Takes a python dict as nvram'''
    @PyPlugin.ppp_export
    def set_nvram(self,nvram):
        self.nvram = nvram
    '''
    set an int as a config value given to nvram init
    '''
    @PyPlugin.ppp_export
    def set_conf(self,conf):
        self.conf = conf
    @PyPlugin.ppp_export
    def nvram_byte_str(self):
        bytestr = b""
        for x in self.nvram.keys():
            val = self.nvram[x]
            if b"\x00" != val:
                bytestr += x.encode() +b"=" +val
        return bytestr

    def get_int(self, cpu, args):
        key = args[1]
        try:
            result = self.nvram[key]
            vali = int(result.decode().strip('\x00'))
            if not self.ppp_run_cb("NVRAM_GET_INT",cpu,key,vali):
                self.panda.arch.set_retval(cpu,vali,convention='syscall')
        except:
            self.panda.arch.set_retval(cpu, 0,convention='syscall')
         
    def set(self, cpu, args):
        #import ipdb;ipdb.set_trace()
        key = args[1]
        buf = args[2]
        if not self.ppp_run_cb("NVRAM_SET",cpu,key,buf):
            self.add_nvram(key,buf.encode()+b'\0')
        with open(self.write_file, "a") as f:
            f.write(f"\n{self.nvram}\n")
        
    def get_buf(self, cpu, args):
        key = args[1]
        buf = int(args[2], 16)
        sz = int(args[3])
        try:
            b = self.nvram[key]
            if len(b) > sz:
                a = b[:sz-1] + b'\0'
            else:
                a = b
            if not self.ppp_run_cb("NVRAM_GET",cpu,key,buf,sz, a,b):
                self.panda.virtual_memory_write(cpu, buf,a)
                self.panda.arch.set_retval(cpu, 1,'syscall')
        except:
            if not self.ppp_run_cb("NVRAM_GET",cpu,key,buf,sz, None, None):
                self.panda.arch.set_retval(cpu, self.MAGIC_VAL,'syscall')
    def unset(self,cpu, args):
        key = args[1]
        try:
            self.nvram.pop(key)
            self.panda.arch.set_retval(cpu, 1)
        except:
            self.panda.arch.set_retval(cpu, 0)

    def set_int(self,cpu,args):
        key = args[1]
        vali = int(args[2])
        if not self.ppp_run_cb("NVRAM_SET_INT",cpu,key,vali):
            self.nvram[key] = args[2].encode() + b'\0'
            self.panda.arch.set_retval(cpu,int.from_bytes(vali.to_bytes(self.panda.bits, 'little',signed=True), 'little'),'syscall')
    
    def getall(self,cpu,args):
        buf = int(args[1], 16)
        sz = int(args[2])
        try:
            b = self.nvram_byte_str()
            size = b[:sz].rfind(b"\0")
            if not self.ppp_run_cb("NVRAM_GETALL",cpu,buf,sz,b,b[:size+1]):
                self.panda.virtual_memory_write(cpu, buf,b[:size+1])
                self.panda.arch.set_retval(cpu, 1,'syscall')
        except:
            self.panda.arch.set_retval(cpu, self.MAGIC_VAL,'syscall')
    '''Current CALLBACKS
        NVRAM_BLOCK_ON_ALL
        NVRAM_INIT
        NVRAM_GET
        NVRAM_GETALL
        NVRAM_SET
        NVRAM_GET_INT
        NVRAM_SET_INT
        NVRAM_LIST_ADD
    '''
    def create_callbacks(self):
        self.ppp_cb_boilerplate("NVRAM_BLOCK_ON_ALL")
        self.ppp_cb_boilerplate("NVRAM_INIT")
        self.ppp_cb_boilerplate("NVRAM_GET")
        self.ppp_cb_boilerplate("NVRAM_GETALL")
        self.ppp_cb_boilerplate("NVRAM_SET")
        self.ppp_cb_boilerplate("NVRAM_GET_INT")
        self.ppp_cb_boilerplate("NVRAM_SET_INT")
        self.ppp_cb_boilerplate("NVRAM_LIST_ADD")