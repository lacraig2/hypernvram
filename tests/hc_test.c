#include <stdint.h>
#define MAGIC_VALUE 5
#include "hypercall.h"
#include <stdio.h>

int main(){
    char* hello = "hello world!\n";
    int out = hc(0x1,&hello,1);
    printf("out: %x\n", out);
    return 0;
}
