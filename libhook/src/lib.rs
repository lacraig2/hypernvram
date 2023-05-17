use std::collections::HashMap;
use std::os::raw::{c_char, c_void};
use std::ffi::CStr;
use libc::{dlsym as orig_dlsym, RTLD_NEXT};
use lazy_static::lazy_static;
use std::sync::Mutex;


struct Shellcode(*mut c_void);

unsafe impl Sync for Shellcode {}
unsafe impl Send for Shellcode {}

lazy_static! {
    //static ref SHIM_FUNCTIONS: HashMap<String, Shellcode> = HashMap::new();
    static ref SHIM_FUNCTIONS: Mutex<HashMap<String, Shellcode>> = Mutex::new(HashMap::new());
}


extern "C" {
    fn my_shim_function(); // Placeholder for a shim function
}

#[no_mangle]
pub extern "C" fn dlsym(handle: *mut c_void, symbol: *const c_char) -> *mut c_void {
    let real_dlsym: extern "C" fn(*mut c_void, *const c_char) -> *mut c_void;
    unsafe {
        real_dlsym = std::mem::transmute(orig_dlsym(RTLD_NEXT, b"dlsym\0".as_ptr() as *const c_char));
    }

    let symbol_str = unsafe { CStr::from_ptr(symbol).to_str().unwrap() };

    let shims = &SHIM_FUNCTIONS.lock().unwrap();
    if let Some(&ref shim) = shims.get(symbol_str) {
        println!("Intercepted symbol: {}, shim at {:?}", symbol_str, shim.0);
        //shim.0
        let real_addr = real_dlsym(handle, symbol);
        real_addr
    } else {
        let real_addr = real_dlsym(handle, symbol);
        real_addr
    }
}

#[ctor::ctor]
fn constructor() {
    // Here, you'd issue a hypercall to get the list of functions to intercept
    // Then, for each function, generate a shim function that issues a unique hypercall
    // This is a non-trivial task and requires a deep understanding of the ABI and calling conventions
    // For the sake of this example, let's assume we have a function `generate_shim` that does this
    
    //let shims = &SHIM_FUNCTIONS;
    //shims.insert("nvram_get".to_string(), generate_shim("nvram_get"));
    //shims.insert("nvram_set".to_string(), generate_shim("nvram_set"));

    SHIM_FUNCTIONS.lock().unwrap().insert("nvram_get".to_string(), generate_shim("nvram_get"));
}

fn generate_shim(_name: &str) -> Shellcode {
    // Placeholder for a function that generates a shim function at runtime
    // This function would generate machine code for a function that issues a unique hypercall
    // The details of how to do this depend on your specific requirements and the target architecture
    //my_shim_function as Shellcode
    //Shellcode(my_shim_function as *mut c_void)
    Shellcode(std::ptr::null_mut())
}