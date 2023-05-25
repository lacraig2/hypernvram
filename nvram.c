#include <dirent.h>
#include <errno.h>
#include <limits.h>
#include <mntent.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ipc.h>
#include <sys/mount.h>
#include <sys/sem.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <mntent.h>

#include "alias.h"
#include "nvram.h"
#include "config.h"
#include "hypercall.h"

/* Weak symbol definitions for library functions that may not be present */

static int firmae_nvram = 0; // Controls some behavior later

struct nvram_op {
    char key[BUFFER_SIZE];
    union {
        char outbuf[BUFFER_SIZE];
        int outint;
    };
    size_t size;
};

static nvram_op pending;

// XXX this used to create the following file:
// /var/run/nvramd.pid: "Checked by certain Ralink routers"

int nvram_init(void) {
    if (hc(NVRAM_INIT, NULL, 0) != 0) {
        return E_FAILURE;
    }

    return E_SUCCESS;
}

int nvram_reset(void) {
    if (hc(NVRAM_RESET, NULL, 0) != 0) {
        return E_FAILURE;
    }
    return E_SUCCESS;
}

int nvram_clear(void) {
    if (hc(NVRAM_CLEAR, NULL, 0) != 0) {
        return E_FAILURE;
    }
    return E_SUCCESS;
}

int nvram_close(void) {
    // Do we need a HC?
    return E_SUCCESS;
}

// Actual get/set functions


char *nvram_get(const char *key) {
// Some routers pass the key as the second argument, instead of the first.
// We attempt to fix this directly in assembly for MIPS if the key is NULL.
#if defined(mips)
    if (!key) {
        asm ("move %0, $a1" :"=r"(key));
    }
#endif

    // We set key to the pending key and size to the outbuf size
    // on return we get the value and it's size
    strncpy(pending.key, key, MIN(sizeof(pending.key), strlen(key)));
    pending.size = sizeof(pending.outbuf);

    if (hc(NVRAM_GET, &pending, sizeof(pending)) != 0) {
        return NULL;
    }

    // Allcoate buffer
    return strndup(pending.outbuf, pending.size);
}

char *nvram_safe_get(const char *key) {
    char* ret = nvram_get(key);
    return ret ? ret : strdup("");
}

char *nvram_default_get(const char *key, const char *val) {
    char *ret = nvram_get(key);

    if (ret) {
        return ret;
    }

    if (val && nvram_set(key, val)) {
        return nvram_get(key);
    }

    return NULL;
}

int nvram_get_buf(const char *key, char *buf, size_t sz) {
    if (!buf) {
        //PRINT_MSG("NULL output buffer, key: %s!\n", key);
        return E_FAILURE;
    }

    strncpy(pending.key, key, MIN(sizeof(pending.key), strlen(key)));
    pending.size = sz;

    if (hc(NVRAM_GET_BUF, &pending, sizeof(pending)) != 0) {
        return E_FAILURE;
    }

    // Success. outbuf contains sz bytes
    strncpy(buf, pending.outbuf, pending.sz);
    return E_SUCCESS;
}

int nvram_get_int(const char *key) {
    strncpy(pending.key, key, MIN(sizeof(pending.key), strlen(key)));

    if (hc(NVRAM_GET_INT, &pending, sizeof(pending)) != 0) {
        return E_FAILURE;
    }
    return pending.outint;
}

int nvram_getall(char *buf, size_t len) {
    char buffer[PATH_MAX];
    
    if (!buf || !len) {
        PRINT_MSG("%s\n", "NULL buffer or zero length!");
        return E_FAILURE;
    }

    if (hc(NVRAM_GETALL, &buffer, sizeof(buffer)) != 0) {
        return E_FAILURE;
    }
    return E_SUCCESS;
}




int nvram_list_add(const char *key, const char *val) {
    char buffer[PATH_MAX];
    snprintf(buffer, sizeof(buffer)-1, "NVRAM_LIST_ADD (%s) (%s)", key, val);
    PRINT_MSG("%s\n", buffer);
    hc(buffer);

    struct nvram_op op;

    strncpy(op.key, buf, sizeof(op.key));
    strncpy(op.value, val, sizeof(op.value));
    op.size = strlen(val);

    return *(int*)buffer;
}

char *nvram_list_exist(const char *key, const char *val, int magic) {
    char *pos = NULL;

    if (nvram_get_buf(key, temp, BUFFER_SIZE) != E_SUCCESS) {
        return E_FAILURE;
    }

    PRINT_MSG("%s ?in %s (%s)\n", val, key, temp);

    if (!val) {
        return (magic == LIST_MAGIC) ? NULL : (char *) E_FAILURE;
    }

    while ((pos = strtok(!pos ? temp : NULL, LIST_SEP))) {
        if (!strcmp(pos + 1, val)) {
            return (magic == LIST_MAGIC) ? pos + 1 : (char *) E_SUCCESS;
        }
    }

    return (magic == LIST_MAGIC) ? NULL : (char *) E_FAILURE;
}

int nvram_list_del(const char *key, const char *val) {
    char *pos;

    if (nvram_get_buf(key, temp, BUFFER_SIZE) != E_SUCCESS) {
        return E_SUCCESS;
    }

    PRINT_MSG("%s = %s - %s\n", key, temp, val);

    if (!val) {
        return E_FAILURE;
    }

    // This will overwrite the temp buffer, but it is OK.
    if ((pos = nvram_list_exist(key, val, LIST_MAGIC))) {
        while (*pos && *pos != LIST_SEP[0]) {
            *pos++ = LIST_SEP[0];
        }
    }

    return nvram_set(key, temp);
}

int nvram_set(const char *key, const char *val) {
    char buffer[PATH_MAX];
    snprintf(buffer, sizeof(buffer)-1, "NVRAM_SET (%s) (%s)", key, val);
    hc(buffer);
    return E_SUCCESS;
}

int nvram_set_int(const char *key, const int val) {
    char buffer[PATH_MAX];
    snprintf(buffer, sizeof(buffer)-1, "NVRAM_SET_INT (%s) (%d)", key, val);
    hc(buffer);
    return E_SUCCESS;
}

static int nvram_set_default_table(const char *tbl[]) {
    size_t i = 0;

    while (tbl[i]) {
        nvram_set(tbl[i], tbl[i + 1]);
        i += (tbl[i + 2] != 0 && tbl[i + 2] != (char *) 1) ? 2 : 3;
    }

    return E_SUCCESS;
}

int nvram_unset(const char *key) {
    char buffer[PATH_MAX];
    if (!key) {
        PRINT_MSG("%s\n", "NULL key!");
        return E_FAILURE;
    }
    snprintf(buffer, sizeof(buffer)-1, "NVRAM_UNSET (%s)", key);
    int ret = hc(buffer);
    PRINT_MSG("= %d\n",ret);
    return *(int*)buffer;
}

int nvram_safe_unset(const char *key) {
    // If we have a value for this key, unset it. Otherwise no-op
    // Always return E_SUCCESS(?)
    char* ret = nvram_get(key);

    if (nvram_get_buf(key, temp, BUFFER_SIZE) == E_SUCCESS) {
      nvram_unset(key);
    }
    return E_SUCCESS;
}

int nvram_match(const char *key, const char *val) {
    if (!key) {
        PRINT_MSG("%s\n", "NULL key!");
        return E_FAILURE;
    }

    if (nvram_get_buf(key, temp, BUFFER_SIZE) != E_SUCCESS) {
        return !val ? E_SUCCESS : E_FAILURE;
    }

    PRINT_MSG("%s (%s) ?= \"%s\"\n", key, temp, val);

    if (strncmp(temp, val, BUFFER_SIZE)) {
        PRINT_MSG("%s\n", "false");
        return E_FAILURE;
    }

    PRINT_MSG("%s\n", "true");
    return E_SUCCESS;
}

int nvram_invmatch(const char *key, const char *val) {
    if (!key) {
        PRINT_MSG("%s\n", "NULL key!");
        return E_FAILURE;
    }

    PRINT_MSG("%s ~?= \"%s\"\n", key, val);
    return !nvram_match(key, val);
}

int nvram_commit(void) {
    return E_SUCCESS;
}

int parse_nvram_from_file(const char *file)
{
    FILE *f;
    char *buffer;
    int fileLen=0;

    if((f = fopen(file, "rb")) == NULL){
        PRINT_MSG("Unable to open file: %s!\n", file);
        return E_FAILURE;
    }

    /* Get file length */
    fseek(f, 0, SEEK_END);
    fileLen = ftell(f);
    rewind(f);

    /* Allocate memory */
    buffer = (char*)malloc(sizeof(char) *fileLen);
    fread(buffer, 1, fileLen, f);
    fclose(f);

    /* split the buffer including null byte */
    #define LEN 1024
    int i=0,j=0,k=0; int left = 1;
    char *key="", *val="";
    char larr[LEN]="", rarr[LEN]="";

    for(i=0; i < fileLen; i++)
    {
        char tmp[4];
        sprintf(tmp, "%c", *(buffer+i));

        if (left==1 && j<LEN)
            larr[j++] = tmp[0];
        else if(left==0 && k<LEN)
            rarr[k++] = tmp[0];

        if(!memcmp(tmp,"=",1)){
            left=0;
            larr[j-1]='\0';
        }
        if (!memcmp(tmp,"\x00",1)){
            key = larr; val = rarr;
            nvram_set(key, val);
            j=0; k=0; left=1;
            memset(larr, 0, LEN); memset(rarr, 0, LEN);
        }
    }
    return E_SUCCESS;
}

#ifdef FIRMAE_KERNEL
//DIR-615I2, DIR-615I3, DIR-825C1 patch
int VCTGetPortAutoNegSetting(char *a1, int a2){
    PRINT_MSG("%s\n", "Dealing wth ioctl ...");
    return 0;
}

// netgear 'Rxxxx' series patch to prevent infinite loop in httpd
int agApi_fwGetFirstTriggerConf(char *a1)
{
    PRINT_MSG("%s\n", "agApi_fwGetFirstTriggerConf called!");
    return 1;
}

// netgear 'Rxxxx' series patch to prevent infinite loop in httpd
int agApi_fwGetNextTriggerConf(char *a1)
{
    PRINT_MSG("%s\n", "agApi_fwGetNextTriggerConf called!");
    return 1;
}
#endif

// Hack to use static variables in shared library
#include "alias.c"
