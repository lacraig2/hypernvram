#include <stdint.h>
#include "hypercall.h"
#include <stdio.h>

int main(){
    int out = hc("hello world!\n");
    printf("out: %x\n", out);
    return 0;
}
