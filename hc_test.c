#include <stdint.h>
#include "hypercall.h"
#include <stdio.h>

int main(){
    char* hello = "hello world!\n";
    int out = hc(&hello,1);
    printf("out: %x\n", out);
    return 0;
}
