#define MAGIC_VAL 0x31838188
#define ERROR_VAL 0x12345678

#if defined(__x86_64__)
static inline int hc(char* s) {
    uint64_t eax = MAGIC_VAL;
    uint64_t ret = ERROR_VAL;

    asm __volatile__(
	 "movq %1, %%rax \t\n\
     movq %2, %%rbx \t\n\
     cpuid \t\n\
     movq %%rax, %0 \t\n\
    "
	: "=g"(ret) /* output operand */
	: "g" (eax),  "g" (s) /* input operands */
	: "eax", "ebx", "ecx", "edx" /* clobbered registers */
    );

    return ret;
}

#elif defined(__i386__) && !defined(__x86_64__)
static inline int hc(char* s) {
    uint32_t eax = MAGIC_VAL;
    uint32_t ret = ERROR_VAL;

    asm __volatile__(
	 "movl %1, %%eax \t\n\
     movl %2, %%ebx \t\n\
     cpuid \t\n\
     movl %%eax, %0 \t\n\
    "
	: "=g"(ret) /* output operand */
	: "g" (eax),  "g" (s) /* input operands */
	: "eax", "ebx", "ecx", "edx" /* clobbered registers */
    );

    return ret;
}
#elif defined(__arm__)
static inline int hc(char *s) {
    unsigned long r0 = MAGIC_VAL;
    int ret = ERROR_VAL;
    char* action = s;


    asm __volatile__(
    "push {r0-r4} \t\n\
     ldr r0, %1 \t\n\
     ldr r1, %2 \t\n\
     ldr r2, %3 \t\n\
     ldr p7, 0, r0, c0, c0, 0 \t\n\
     sdr r0, %0 \t\n\
     pop {r0-r4} \t\n\
    "
    : "=g"(ret) /* output operand */
    : "g" (r0), "g" (action), "g" (s) /* input operands */
    : "r0", "r1", "r2", "r3", "r4" /* clobbered registers */
    );

    return ret;
}
#elif defined(mips) || defined(__mips__) || defined(__mips)
static inline int hc(void *s) {
    unsigned long r0 = MAGIC_VAL;
    int ret = ERROR_VAL;

    asm __volatile__(
    "movz $0, $0, $0\t\n"
    : "=g"(ret) /* output operand */
    : "g" (r0), "g" (s) /* input operands */
    : "a0", "a1", "a2", "a3" /* clobbered registers */
    );

    return ret;
}
#else
#error Unsupported platform.
#endif