#include <stdio.h>
#include "nvram.h"

int main(){
    char* value = nvram_get("hello");
    printf("Got value %s\n", value);
    return 0;
}