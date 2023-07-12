
from pandare import PyPlugin, Panda
import ipaddress
import socket
import os
'''
Interface to LibNvram Hypercalls.

Register callbacks via 
panda.pyplugins.ppp.NVramHC.ppp_reg_cb("nvram_get",get_ipdb_call)
For NVRAM_GET exmaple
TODO: Setup actual list add. Handle additional nvram hooks
'''
MAGIC_VALUE = 0x4e564843
NVRAM_CLOSE = 0x31838180 
NVRAM_INIT = 0x31838181 
NVRAM_CLEAR = 0x31838182 
NVRAM_LIST_ADD = 0x31838183 
NVRAM_GET_BUF = 0x31838184 
NVRAM_GET_INT = 0x31838185 
NVRAM_GETALL = 0x31838186 
NVRAM_SET = 0x31838187 
NVRAM_SET_INT = 0x31838188 
NVRAM_UNSET = 0x31838189 
NVRAM_COMMIT = 0x3183818a 
ERROR_VAL = 0x12345678
class NVramHC(PyPlugin):
    def __init__(self, panda: Panda):
        print("Loading Nvram HyperCall plugin")
        super().__init__(panda)
        self.panda = panda
        outdir = self.get_arg("outdir")
        self.log = self.get_arg_bool("log")
        self.write_file = None
        if self.log:
            self.write_file = os.path.join(outdir,"nvram.log")
            open(self.write_file, "w").close() #Clear the file
        self.nvram:dict = self.get_arg("nvram")
        if self.nvram is None:
            self.nvram = {}
        self.create_callbacks()

        self.conf = 0
        @panda.cb_guest_hypercall
        def hypercall(cpu):
            magic = panda.arch.get_arg(cpu, 1, convention="syscall")
            if  panda.arch.get_arg(cpu, 0, convention="syscall") != MAGIC_VALUE:
                print(f"F[ound hypercall, but value was {hex(panda.arch.get_arg(cpu, 0, convention='syscall'))}")
                return False
            len = panda.arch.get_arg(cpu, 2, convention='syscall')
            pointer_size = panda.bits //8
            argptr =  panda.arch.get_arg(cpu, 3, convention='syscall')
            argstr = []
            for x in range(0,len):
                addr = int.from_bytes(panda.virtual_memory_read(cpu, argptr + ( pointer_size * x), pointer_size),'little')
                argstr.append(panda.read_str(cpu, addr))
            if self.log:
                with open(self.write_file, "a") as f:
                    f.write(f"\n{magic:x} {argstr}\n")
            block = self.ppp_run_cb("nvram_block_all",cpu, magic, argstr)
            if block:
                return True
            if NVRAM_GET_INT == magic:
                self.get_int(cpu,argstr)
            elif NVRAM_GET_BUF == magic:
                self.get_buf(cpu,argstr)
            elif NVRAM_SET_INT == magic:
                self.set_int(cpu,argstr)
            elif NVRAM_UNSET == magic:
                self.unset(cpu,argstr)
            elif NVRAM_SET == magic:
                self.set(cpu,argstr)
            elif NVRAM_LIST_ADD == magic:
                if not self.ppp_run_cb("nvram_list_add",cpu,argstr):
                    self.set(cpu,argstr)
            elif NVRAM_CLEAR == magic:
                self.nvram.clear()
            elif NVRAM_GETALL == magic:
                self.getall(cpu,argstr)
            elif NVRAM_INIT == magic:
                if not self.ppp_run_cb("nvram_init",cpu):
                    self.panda.arch.set_retval(cpu,self.conf)
            elif NVRAM_COMMIT ==magic:
                #TODO commit impl
                pass
            else:
                print(magic,argstr)
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
        key = args[0]
        try:
            result = self.nvram[key]
            vali = int(result.decode().strip('\x00'))
            if not self.ppp_run_cb("nvram_get_int",cpu,key,vali):
                self.panda.arch.set_retval(cpu,vali,convention='syscall')
        except:
            self.panda.arch.set_retval(cpu, 0,convention='syscall')
         
    def set(self, cpu, args):
        key = args[0]
        buf = args[1]
        if not self.ppp_run_cb("nvram_set",cpu,key,buf):
            self.add_nvram(key,buf)
        if self.log:
            with open(self.write_file, "a") as f:
                f.write(f"\n{self.nvram}\n")
        
    def get_buf(self, cpu, args):
        key = args[0]
        buf = int(args[1], 16)
        sz = int(args[2])
        try:
            b = self.nvram[key]
        except:
            if not self.ppp_run_cb("nvram_get",cpu,key,buf,sz, None, None):
                self.panda.arch.set_retval(cpu, NVRAM_GET_BUF,'syscall')
                return
        if len(b) > sz:
            a = b[:sz-1] + b'\0'
        else:
            a = b
        if not self.ppp_run_cb("nvram_get",cpu,key,buf,sz, a,b):
            self.panda.virtual_memory_write(cpu, buf,a)
            self.panda.arch.set_retval(cpu, 0,'syscall')

    def unset(self,cpu, args):
        key = args[0]
        try:
            self.nvram.pop(key)
            if self.log:
                with open(self.write_file, "a") as f:
                    f.write(f"\n{self.nvram}\n")
            self.panda.arch.set_retval(cpu, 1)
        except:
            self.panda.arch.set_retval(cpu, 0)

    def set_int(self,cpu,args):
        key = args[0]
        vali = int(args[1])
        if not self.ppp_run_cb("nvram_set_int",cpu,key,vali):
            self.add_nvram(key,args[1])
            if self.log:
                with open(self.write_file, "a") as f:
                    f.write(f"\n{self.nvram}\n")
            self.panda.arch.set_retval(cpu,int.from_bytes(vali.to_bytes(self.panda.bits, 'little',signed=True), 'little'),'syscall')
    
    def getall(self,cpu,args):
        buf = int(args[0], 16)
        sz = int(args[1])
        try:
            b = self.nvram_byte_str()
            size = b[:sz].rfind(b"\0")
            if not self.ppp_run_cb("nvram_getall",cpu,buf,sz,b,b[:size+1]):
                self.panda.virtual_memory_write(cpu, buf,b[:size+1])
                self.panda.arch.set_retval(cpu, 1,'syscall')
        except:
            self.panda.arch.set_retval(cpu, NVRAM_GETALL,'syscall')
    '''Current CALLBACKS
        nvram_block_all(cpu, magic, argstr)
        nvram_init(cpu)
        nvram_get(cpu,key,buf_ptr,size, shortened_buf,entire_buf)
        nvram_getall(cpu,key,vali)
        nvram_set(cpu,key,buf)
        nvram_get_int(cpu,key,vali)
        nvram_set_int(cpu,key,vali)
        nvram_list_add(cpu,argstr)
    '''
    def create_callbacks(self):
        self.ppp_cb_boilerplate("nvram_block_all")
        self.ppp_cb_boilerplate("nvram_init")
        self.ppp_cb_boilerplate("nvram_get")
        self.ppp_cb_boilerplate("nvram_getall")
        self.ppp_cb_boilerplate("nvram_set")
        self.ppp_cb_boilerplate("nvram_get_int")
        self.ppp_cb_boilerplate("nvram_set_int")
        self.ppp_cb_boilerplate("nvram_list_add")