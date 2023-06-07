#define MAGIC_VAL 0x31838188

int strnlen_n(char* s, int max_len){
    int i = 0;
    while (i < max_len && s[i] != '\0'){
        i++;
    }
    return i;
}

// #if defined(__x86_64__)
#if defined(__x86_64__)
static inline int hc(char **s,int len) {
    uint64_t eax = MAGIC_VAL;
    uint64_t ret = MAGIC_VAL;
    for(int i = 0; i< len; i++){
        PRINT_MSG("%s\n",s[i]);
        strnlen_n(s[i],0x1000);
    }
    asm __volatile__(
	"movq %1, %%rax \t\n\
     movq %2, %%rdi \t\n\
     movq %3, %%rsi \t\n\
     cpuid \t\n\
     mov %%rax, %0 \t\n\
    "
	: "=m" (ret) /* output operand */
	: "g" (eax), "g" (len), "g" (s) /* input operands */
	: "rdi", "rsi", "rdx", "eax" /* clobbered registers */
    );

    return ret;
}
#elif defined(__i386__) && !defined(__x86_64__)
static inline int hc(char **s,int len) {
    int eax = MAGIC_VAL;
    int ret = MAGIC_VAL;
    for(int i = 0; i< len; i++){
        strnlen_n(s[i],0x1000);
    }

    asm __volatile__(
	"mov %1, %%eax \t\n\
     mov %2, %%ebx \t\n\
     mov %3, %%ecx \t\n\
     cpuid \t\n\
     mov %%eax, %0 \t\n\
    "
	: "=g" (ret) /* output operand */
	: "g" (eax), "g" (len), "g" (s) /* input operands */
	: "eax", "ebx", "ecx", "edx" /* clobbered registers */
    );

    return ret;
}
#elif defined(__arm__)
static inline __attribute__((always_inline)) int hc(char **s, int len) {
    unsigned long r0 = MAGIC_VAL;
    int ret = MAGIC_VAL;
    for(int i = 0; i< len; i++){
        strnlen_n(s[i],0x1000);
    }
        asm __volatile__("push {%%r0-%%r4} \t\n\
        mov %%r7, %1 \t\n\
        mov %%r0, %2 \t\n\
        mov %%r1, %3 \t\n\
        mov %%r2, %4 \t\n\
        mcr p7, 0, r0, c0, c0, 0 \t\n\
        mov %0, %%r0 \t\n\
        pop {%%r0-%%r4} \t\n"
      : "=g"(ret) /* no output registers */
      : "r" (r0), "r" (len), "r" (s), "r" (0) /* input registers */
      : "r0", "r1", "r2", "r3", "r4" /* clobbered registers */
      );
    return ret;
}
#elif defined(__mips64)
static inline int hc(void *s) {
    unsigned int action = (unsigned int) strnlen_n(s, 0x1000);
    unsigned long r0 = MAGIC_VAL;
    int ret = MAGIC_VAL;

    asm __volatile__(
    "move $2, %1\t\n"
    "move $4, %2\t\n"
    "move $5, %3\t\n"
    "movz $0, $0, $0\t\n"
    "move %0, $2\t\n"
    : "=g"(ret) /* output operand */
    : "r" (r0), "r" (action), "r" (s)  /* input operands */
    : "a0", "a1", "a2", "a3" /* clobbered registers */
    );

    return ret;
}
#elif defined(mips) || defined(__mips__) || defined(__mips)
static inline int hc(void *s) {
    unsigned int action = (unsigned int) strnlen_n(s, 0x1000);
    unsigned long r0 = MAGIC_VAL;
    int ret = MAGIC_VAL;

    asm __volatile__(
    "move $2, %1\t\n"
    "move $4, %2\t\n"
    "move $5, %3\t\n"
    "movz $0, $0, $0\t\n"
    "move %0, $2\t\n"
    : "=g"(ret) /* output operand */
    : "r" (r0), "r" (action), "r" (s)  /* input operands */
    : "a0", "a1", "a2", "a3" /* clobbered registers */
    );

    return ret;
}
#elif defined(__aarch64__)
static inline __attribute__((always_inline)) int hc(char *s) {
    unsigned int action = (unsigned int) strnlen_n(s, 0x1000);
    unsigned long r0 = MAGIC_VAL;
    int ret = MAGIC_VAL;

    asm __volatile__("stp x0, x1, [sp, #-16]! \t\n\
        stp x2, x3, [sp, #-16]! \t\n\
        mov x8, %1 \t\n\
        mov x0, %2 \t\n\
        mov x1, %3 \t\n\
        mov x2, %4 \t\n\
        msr S0_0_c5_c0_0, xzr \t\n\
        mov %0, x0 \t\n\
        ldp x0, x1, [sp], #16 \t\n\
        ldp x2, x3, [sp], #16 \t\n"
      : "=g"(ret) /* no output registers */
      : "r" (r0), "r" (action), "r" (s), "r" (0) /* input registers */
      : "x0", "x1", "x2", "x3", "x4" /* clobbered registers */
      );
    return ret;
}
#else
#error Unsupported platform.
#endif