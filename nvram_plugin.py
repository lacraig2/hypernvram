
from pandare import PyPlugin, Panda
import ipaddress
import socket
import os

'''
Interface to LibNvram Hypercalls.

Register callbacks via 
panda.pyplugins.ppp.NVRAM_Hypercall.ppp_reg_cb("nvram_get", get_ipdb_call)
For NVRAM_GET example
TODO: Setup actual list add. Handle additional nvram hooks
'''
RETRY = 0xDEADBEEF
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
CACHE = 0xCA000000
CONTROL = 0xCE000000
UNSET_CACHE = 0x31838170


class NVRAM_Hypercall(PyPlugin):
    def __init__(self, panda: Panda):
        print("Loading NVRAM_Hypercall plugin")
        super().__init__(panda)
        self.panda = panda
        outdir = self.get_arg("outdir")
        self.log = self.get_arg_bool("log")
        self.write_file = None
        if self.log:
            self.write_file = os.path.join(outdir,"nvram.log")
            open(self.write_file, "w").close() # Clear the file
        self.nvram:dict = self.get_arg("nvram")
        if self.nvram is None:
            self.nvram = {}
        self.create_callbacks()
        self.missing = {}
        self.conf = 0
        self.cache = {}
        self.uncache = set()
        self.cached = {}

        @panda.cb_guest_hypercall
        def hypercall(cpu):
            magic = panda.arch.get_arg(cpu, 0, convention='syscall')
            hc_type = panda.arch.get_arg(cpu, 1, convention="syscall")
            argptr =  panda.arch.get_arg(cpu, 2, convention='syscall')
            length = panda.arch.get_arg(cpu, 3, convention='syscall')
            pointer_size = panda.bits // 8
            if magic != MAGIC_VALUE:
                print(f"Found hypercall, but value was {hex(hc_type)}")
                return False
            try:
                argv =  panda.virtual_memory_read(cpu, argptr, pointer_size * length, fmt="ptrlist")
            except ValueError:
                print("RETRY NVRAM argv virt.mem.read") 
                panda.arch.set_retval(cpu, self.panda.to_unsigned_guest(RETRY))
                return True
            panda.arch.set_retval(cpu, MAGIC_VALUE)
            if self.log:
                with open(self.write_file, "a") as f:
                    f.write(f"\n{hc_type:x} {argv}\n")
            block = self.ppp_run_cb("nvram_block_all", cpu, hc_type, argv)
            if block:
                return True
            if hc_type == NVRAM_GET_INT:
                self.get_int(cpu, argv)
            elif hc_type == NVRAM_GET_BUF:
                self.get_buf(cpu, argv)
            elif hc_type == NVRAM_SET_INT:
                self.set_int(cpu, argv)
            elif hc_type == NVRAM_UNSET:
                self.unset(cpu, argv)
            elif hc_type == NVRAM_SET:
                self.set(cpu, argv)
            elif hc_type == NVRAM_LIST_ADD:
                if not self.ppp_run_cb("nvram_list_add", cpu, argv):
                    self.set(cpu, argv)
            elif hc_type == NVRAM_CLEAR:
                self.nvram.clear()
                self.panda.arch.set_retval(cpu, 0)
            elif hc_type == NVRAM_GETALL:
                self.getall(cpu, argv)
            elif hc_type == NVRAM_INIT:
                if not self.ppp_run_cb("nvram_init", cpu):
                    self.panda.arch.set_retval(cpu, self.conf)
            elif hc_type == NVRAM_COMMIT:
                #TODO commit impl
                pass
            elif hc_type == UNSET_CACHE:
                self.unset_cache(cpu, argv)
            else:
                print(hex(hc_type), argv)
            return True
    
    # Calling convention for exported functions: panda.pyplugins.ppp.NVRAM_Hypercall.{func_name}(func_params)
    '''
    creates a copy of current nvram dictionary 
    '''
    @PyPlugin.ppp_export
    def get_nvram(self):
        self.nvram.copy()
    @PyPlugin.ppp_export
    def add_nvram(self, key, val):
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
    def set_nvram(self, nvram):
        self.nvram = nvram
    @PyPlugin.ppp_export
    def set_cache(self, cache):
        self.cache = cache
    @PyPlugin.ppp_export
    def add_cache(self, key, conf):
        self.cache[key] = conf
        self.uncache.pop(key)
    @PyPlugin.ppp_export
    def remove_cache(self, key):
        self.cache.pop(key)
        self.uncache.append(key)
    '''
    set an int as a config value given to nvram init
    '''
    @PyPlugin.ppp_export
    def set_conf(self, conf):
        self.conf = conf
    @PyPlugin.ppp_export
    def nvram_byte_str(self):
        bytestr = b""
        for x in self.nvram.keys():
            val = self.nvram[x]
            if b"\x00" != val:
                bytestr += x.encode() + b"=" + val
        return bytestr

    def get_int(self, cpu, argv):
        try:
            key = self.panda.read_str(cpu, argv[0])
        except ValueError:
            print("RETRY NVRAM_GET_INT")
            self.panda.arch.set_retval(cpu, RETRY)
            return
        buf = argv[1]
        if result := self.nvram.get(key, None):
            numstr = result.decode().strip('\x00')
            try:
                num = int(numstr)
            except ValueError:
                num = 0
            vali = self.panda.to_unsigned_guest(num)
            if not self.ppp_run_cb("nvram_get_int", cpu, key, vali):
                try: 
                    self.panda.virtual_memory_write(cpu, buf, vali.to_bytes(4, 'little'))
                    if cache_config := self.cache.get(key, None):
                        self.panda.arch.set_retval(cpu, CACHE | cache_config)
                    elif self.control(cpu):
                        self.panda.arch.set_retval(cpu, 0)
                except ValueError:
                    print("RETRY NVRAM_GET_INT")
                    self.panda.arch.set_retval(cpu, RETRY)
        else:
            if key not in self.missing:
                print(f"Key {key} not found")
            self.missing[key] = self.missing.get(key, 0) + 1
            if self.control(cpu):
                self.panda.arch.set_retval(cpu, 0, convention='syscall')
         
    def set(self, cpu, argv):
        try:
            key = self.panda.read_str(cpu, argv[0])
            buf = self.panda.read_str(cpu, argv[1])
        except ValueError:
            print("RETRY NVRAM_SET")
            self.panda.arch.set_retval(cpu, RETRY)
            return
        if not self.ppp_run_cb("nvram_set", cpu, key, buf):
            self.add_nvram(key, buf)
        self.control(cpu)
        if self.log:
            with open(self.write_file, "a") as f:
                f.write(f"\n{self.nvram}\n")
        
    def get_buf(self, cpu, argv):
        try:
            key = self.panda.read_str(cpu, argv[0])
            sz = int.from_bytes(self.panda.virtual_memory_read(cpu, argv[2], self.panda.bits // 8), 'little')
        except ValueError:
            print("RETRY NVRAM_GET_BUF")
            self.panda.arch.set_retval(cpu, RETRY)
            return
        if "ipdb" in key:
            import ipdb;ipdb.set_trace()
        buf = argv[1]
        b = self.nvram.get(key, None)
        if b == None :
            if not self.ppp_run_cb("nvram_get", cpu, key, buf, sz, None, None):
                self.panda.arch.set_retval(cpu, NVRAM_GET_BUF, 'syscall')
            if key not in self.missing:
                print(f"Key {key} not found")
                self.missing[key] = self.missing.get(key, 0) + 1
            return
        if len(b) > sz:
            a = b[:sz-1] + b'\0'
        else:
            a = b
        if not self.ppp_run_cb("nvram_get", cpu, key, buf, sz, a, b):
            try:
                self.panda.virtual_memory_write(cpu, buf, a)
                if cache_config := self.cache.get(key, None):
                    self.panda.arch.set_retval(cpu, CACHE | cache_config)
                elif self.control(cpu):
                    self.panda.arch.set_retval(cpu, 0, 'syscall')
            except ValueError:
                print("RETRY NVRAM_GET_BUF")
                self.panda.arch.set_retval(cpu, RETRY, 'syscall') 

    def unset(self, cpu, argv):
        try:
            key = self.panda.read_str(cpu, argv[0])
        except ValueError:
            print("RETRY NVRAM_UNSET")
            self.panda.arch.set_retval(cpu, RETRY)
            return
        fail =  self.nvram.pop(key, None)
        if self.log:
            with open(self.write_file, "a") as f:
                f.write(f"\n{self.nvram}\n")
        if fail == None and self.control(cpu):
            self.panda.arch.set_retval(cpu, 0)

    def set_int(self, cpu, argv):
        try:
            key = self.panda.read_str(cpu, argv[0])
            vali = int.from_bytes(self.panda.virtual_memory_read(cpu, argv[1], self.panda.bits // 8), 'little')
        except ValueError:
            print("RETRY NVRAM_SET_INT")
            self.panda.arch.set_retval(cpu, RETRY)
            return
        if not self.ppp_run_cb("nvram_set_int", cpu, key, vali):
            self.add_nvram(key, vali)
            if self.log:
                with open(self.write_file, "a") as f:
                    f.write(f"\n{self.nvram}\n")
            if self.control(cpu):
                self.panda.arch.set_retval(cpu, self.panda.to_unsigned_guest(vali))
    
    def getall(self, cpu, argv):
        buf = argv[0]
        try:
            sz = int.from_bytes(self.panda.virtual_memory_read(cpu, argv[1], self.panda.bits // 8), 'little')
        except ValueError:
            print("RETRY NVRAM_GETALL")
            self.panda.arch.set_retval(cpu, RETRY)
            return
        b = self.nvram_byte_str()
        size = b[:sz].rfind(b"\0")
        if not self.ppp_run_cb("nvram_getall", cpu, buf, sz, b, b[:size + 1]):
            try:
                self.panda.virtual_memory_write(cpu, buf, b[:size + 1])
                if self.control():
                    self.panda.arch.set_retval(cpu, 1, 'syscall')
            except ValueError:
                print("RETRY NVRAM_GETALL")
                self.panda.arch.set_retval(cpu, NVRAM_GETALL, 'syscall')
    
    def unset_cache(self, cpu, argv):
        pid = self.panda.get_current_process(cpu).pid
        if result := self.cached.get(pid, None):
            if len(result.intersection(self.uncache)) > 0:
                key = result.intersection(self.uncache).encode() + b'\0'
                self.panda.virtual_memory_write(cpu, argv[0], key, len(key))
                self.control(cpu)
                
    '''Current CALLBACKS
        nvram_block_all(cpu, hc_type, argv)
        nvram_init(cpu)
        nvram_get(cpu, key, buf_ptr, size, shortened_buf, entire_buf)
        nvram_getall(cpu, key, vali)
        nvram_set(cpu, key, buf)
        nvram_get_int(cpu, key, vali)
        nvram_set_int(cpu, key, vali)
        nvram_list_add(cpu, argv)
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
        #print(self.nvram)
        pass

    def control(self, cpu):
        pid = self.panda.get_current_process(cpu).pid
        if result := self.cached.get(pid, None):
            if len(result.intersection(self.uncache)) > 0:
                self.panda.arch.set_retval(cpu, CONTROL | 1)
                return False
        return True