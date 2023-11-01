#include <stdint.h>
#define MAGIC_VALUE 5
#include "libhc/hypercall.h"
#include <stdio.h>
#include <string.h>

int main(){
    printf("hello world\n");
    char *hello = "hello world!\n";
    int size = strlen(hello);
    void *buffer[3] = {hello, &size};
    int out = hc(0x1,buffer,2);
    printf("out: %x\n", out);
    return 0;
}
