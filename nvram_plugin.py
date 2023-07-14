
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
            length = panda.arch.get_arg(cpu, 2, convention='syscall')
            pointer_size = panda.bits // 8
            argptr =  panda.arch.get_arg(cpu, 3, convention='syscall')
            argstr = [panda.read_str(cpu, addr) for addr in panda.virtual_memory_read(cpu, argptr, pointer_size * length, fmt="ptrlist")]
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
        if type(val) is str:
            value_set = val.encode()
        elif type(val) is bytes:
            value_set = val
        elif type(val) is int:
            value_set = str(val).encode()
        else:
            raise Exception("invalid type")
        self.nvram[key] = value_set + b'\0'
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
        if result := self.nvram.get(key, None):
            numstr = result.decode().strip('\x00')
            try:
                num = int(numstr)
            except ValueError:
                num = 0
            vali = self.panda.ffi.cast("target_ulong", num)
            if not self.ppp_run_cb("nvram_get_int", cpu, key, vali):
                self.panda.arch.set_retval(cpu, vali, convention='syscall')
        else:
            if key not in self.missing:
                print(f"Key {key} not found")
            self.missing[key] = self.missing.get(key,0) +1
            self.panda.arch.set_retval(cpu, 0, convention='syscall')
         
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
        if b := self.nvram.get(key, None):
            if not self.ppp_run_cb("nvram_get",cpu,key,buf,sz, None, None):
                self.panda.arch.set_retval(cpu, NVRAM_GET_BUF,'syscall')
            if key not in self.missing:
                print(f"Key {key} not found")
                self.missing[key] = self.missing.get(key,0) +1
            return
        if len(b) > sz:
            a = b[:sz-1] + b'\0'
        else:
            a = b
        if not self.ppp_run_cb("nvram_get",cpu,key,buf,sz, a,b):
            try:
                self.panda.virtual_memory_write(cpu, buf,a)
                self.panda.arch.set_retval(cpu, 0,'syscall')
            except ValueError:
                self.panda.arch.set_retval(cpu, NVRAM_GET_BUF,'syscall') 

    def unset(self,cpu, args):
        key = args[0]
        fail = -1== self.nvram.pop(key, -1)
        if self.log:
            with open(self.write_file, "a") as f:
                f.write(f"\n{self.nvram}\n")
        if fail:
            self.panda.arch.set_retval(cpu, 0)

    def set_int(self,cpu,args):
        key = args[0]
        vali = int(args[1])
        if not self.ppp_run_cb("nvram_set_int",cpu,key,vali):
            self.add_nvram(key,args[1])
            if self.log:
                with open(self.write_file, "a") as f:
                    f.write(f"\n{self.nvram}\n")
            self.panda.arch.set_retval(cpu,self.panda.to_unsigned_guest(vali))
    
    def getall(self,cpu,args):
        buf = int(args[0], 16)
        sz = int(args[1])
        b = self.nvram_byte_str()
        size = b[:sz].rfind(b"\0")
        if not self.ppp_run_cb("nvram_getall",cpu,buf,sz,b,b[:size+1]):
            try:
                self.panda.virtual_memory_write(cpu, buf,b[:size+1])
                self.panda.arch.set_retval(cpu, 1,'syscall')
            except ValueError:
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

    def uninit(self):
        import ipdb
        ipdb.set_trace()
        with open("missing_nvram.txt","w") as f:
            keys = list(self.missing.keys())
            sorted(keys, key=lambda x: self.missing[x])
            for k in keys:
                f.write(f"{k}: {self.missing[k]} \n")
        print(f"Missing NVRAM: {self.missing}")