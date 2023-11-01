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
#include "libhc/hypercall.h"

/* Generate variable declarations for external NVRAM data. */
#define NATIVE(a, b)
#define PATH(a)
#define FIRMAE_PATH(a)
#define FIRMAE_PATH2(a)
#define TABLE(a) \
    extern const char *a[] __attribute__((weak));

NVRAM_DEFAULTS_PATH
#undef TABLE
#undef FIRMAE_PATH2
#undef FIRMAE_PATH
#undef PATH
#undef NATIVE

// https://lkml.org/lkml/2007/3/9/10
#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]) + sizeof(typeof(int[1 - 2 * !!__builtin_types_compatible_p(typeof(arr), typeof(&arr[0]))])) * 0)

#define PRINT_MSG(fmt, ...) do { if (DEBUG) { fprintf(stderr, "%s: "fmt, __FUNCTION__, __VA_ARGS__); } } while (0)

/* Weak symbol definitions for library functions that may not be present */
__typeof__(ftok) __attribute__((weak)) ftok;
__typeof__(setmntent) __attribute__((weak)) setmntent;
void *dlsym(void *restrict handle, const char *restrict symbol);
/* Global variables */
static int init = 0;
static char temp[BUFFER_SIZE];
static int is_load_env = 0;
static int firmae_nvram = 0;
static int config;
static cache_node* cache;
static cache_node* cache_end;
static char* (*DEFAULT_GET)(char*, char*) = NULL;
static void firmae_load_env()
{
    char* env = getenv("FIRMAE_NVRAM");
    if (env && env[0] == 't')
        firmae_nvram = 1;
    is_load_env = 1;
}


int nvram_init(void) {
    FILE *f;
    if (init) {
        PRINT_MSG("%s\n", "Early termination!");
        return E_SUCCESS;
    }
    init = 1;
    PRINT_MSG("%s\n", "Initializing NVRAM...");
    config = hc(NVRAM_INIT, NULL, 0);
    if (config & 1) {
      DEFAULT_GET = dlsym((void*) -1, "nvram_default_get");
    }
    // Checked by certain Ralink routers
    if ((f = fopen("/var/run/nvramd.pid", "w+")) == NULL) {
        PRINT_MSG("Unable to touch Ralink PID file: %s!\n", "/var/run/nvramd.pid");
    }
    else {
        fclose(f);
    }
    return nvram_set_default();
}

int nvram_reset(void) {
    PRINT_MSG("%s\n", "Resetting NVRAM...");

    if (nvram_clear() != E_SUCCESS) {
        PRINT_MSG("%s\n", "Unable to clear NVRAM!");
        return E_FAILURE;
    }

    return nvram_set_default();
}

int nvram_clear(void) {
    PRINT_MSG("%s\n", "Clearing NVRAM...");
    if (hc(NVRAM_CLEAR, NULL, 0)) {
        while(cache != NULL) {
            delete_cached(cache->key);
        }
    }

    return E_SUCCESS;
}

int nvram_close(void) {
    PRINT_MSG("%s\n", "Closing NVRAM...");
    hc(NVRAM_CLOSE, NULL, 0);
    return E_SUCCESS;
}

int nvram_list_add(const char *key, const char *val) {
    void* buffer[2] = {key, val};
    hc(NVRAM_LIST_ADD, buffer, 2);
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

char *nvram_get(const char *key) {
// Some routers pass the key as the second argument, instead of the first.
// We attempt to fix this directly in assembly for MIPS if the key is NULL.
#if defined(mips)
    if (!key) {
        asm ("move %0, $a1" :"=r"(key));
    }
#endif
    //fprintf("nvram_get -> ");
    PRINT_MSG("%s", "-> ");
    return (nvram_get_buf(key, temp, BUFFER_SIZE) == E_SUCCESS) ? strndup(temp, BUFFER_SIZE) : NULL;
}

char *nvram_safe_get(const char *key) {
    char* ret = nvram_get(key);
    return ret ? ret : strdup("");
}

char *nvram_default_get(const char *key, const char *val) {
    if (!init) nvram_init();
    if (DEFAULT_GET) return (*DEFAULT_GET)(key, val);
    char *ret = nvram_get(key);

    PRINT_MSG("%s = %s || %s\n", key, ret, val);

    if (ret) {
        return ret;
    }

    if (val && nvram_set(key, val)) {
        return nvram_get(key);
    }
    return NULL;
}

int nvram_get_buf(const char *key, char *buf, size_t sz) {
    if (!init) {
        nvram_init();
    }
    if (!key) {
        PRINT_MSG("%s\n", "NULL key!");
        return E_FAILURE;
    }
    if (!buf) {
        PRINT_MSG("NULL output buffer, key = %s!\n", key);
        return E_FAILURE;
    }
    if (config & 2) {
        cache_node* target = get_cached(key, 1);
        if (target != NULL) {
            strncpy(buf, target->val, sz);
            return E_SUCCESS;
        }
    }
    void *buffer[3] = {key, buf, &sz};
    int result = hc(NVRAM_GET_BUF, buffer, 3);
    if (result == NVRAM_GET_BUF) {
        PRINT_MSG("%s %s!\n", "Unable to get value for", key);
        return E_FAILURE;
    }
    if (result & CACHE == CACHE) {
        insert_cached_str(key, buf, result & CONTROL_MASK);
    }
    PRINT_MSG("key = \"%s\", val = \"%s\"\n", key, buf);
    return E_SUCCESS;
}

int nvram_get_int(const char *key) {
    if (!init) {
        nvram_init();
    }
    if (!key) {
        PRINT_MSG("%s\n", "NULL key!");
        return E_FAILURE;
    }
    if (config & 2) {
        cache_node* target = get_cached(key, 2);
        if (target != NULL) {
            return target->vali;
        }
    }
    int temp_int = 0;
    void *buf[2] = {key, &temp_int};
    int result = hc(NVRAM_GET_INT, buf, 2);
    PRINT_MSG("key = \"%s\", val = \"%i\"\n", key, temp_int);
    if (result & CACHE == CACHE) {
        insert_cached_int(key, temp_int, result & CONTROL_MASK);
    }
    return temp_int;
}

int nvram_getall(char *buf, size_t len) {
    if (!buf || !len) {
        PRINT_MSG("%s\n", "NULL buffer or zero length!");
        return E_FAILURE;
    }

    void* buffer[2] = {buf, &len};
    hc(NVRAM_GETALL, buffer, 2);
    return E_SUCCESS;
}

int nvram_set(const char *key, const char *val) {
    if (key == NULL || val == NULL) {
        return E_FAILURE;
    }
    if (config & 2) {
        cache_node* target = get_cached(key, 3);
        if (target != NULL) {
            return E_SUCCESS;
        }
    }
    
    void* buffer[2] = {key, val};
    hc(NVRAM_SET, buffer, 2);
    PRINT_MSG("key = \"%s\", val = \"%s\"\n", key, val);
    return E_SUCCESS;
}

int nvram_set_int(const char *key, const int val) {
    if (key == NULL) {
        return E_FAILURE;
    }
    if (config & 2) {
        cache_node* target = get_cached(key, 3);
        if (target != NULL) {
            return E_SUCCESS;
        }
    }    
    char val_ptr[20];
    snprintf(val_ptr, sizeof(val_ptr)-1, "%d", val);
    char* buffer[2] = {key, val_ptr};
    hc(NVRAM_SET_INT, buffer, 2);
    PRINT_MSG("key = \"%s\", val = \"%i\"\n", key, val);
    return E_SUCCESS;
}

int nvram_set_default(void) {
    int ret = nvram_set_default_builtin();
    PRINT_MSG("Loading built-in default values = %d!\n", ret);
    if (!is_load_env) firmae_load_env();

#define NATIVE(a, b) \
    if (!system(a)) { \
        PRINT_MSG("Executing native call to built-in function: %s (%p) = %d!\n", #b, b, b); \
    }

#define TABLE(a) \
    PRINT_MSG("Checking for symbol \"%s\"...\n", #a); \
    if (a) { \
        PRINT_MSG("Loading from native built-in table: %s (%p) = %d!\n", #a, a, nvram_set_default_table(a)); \
    }

#define PATH(a) \
    if (!access(a, R_OK)) { \
        PRINT_MSG("Loading from default configuration file: %s = %d!\n", a, foreach_nvram_from(a, (void (*)(const char *, const char *, void *)) nvram_set, NULL)); \
    }
#define FIRMAE_PATH(a) \
    if (firmae_nvram && !access(a, R_OK)) { \
        PRINT_MSG("Loading from default configuration file: %s = %d!\n", a, foreach_nvram_from(a, (void (*)(const char *, const char *, void *)) nvram_set, NULL)); \
    }
#define FIRMAE_PATH2(a) \
    if (firmae_nvram && !access(a, R_OK)) { \
        PRINT_MSG("Loading from default configuration file: %s = %d!\n", a, parse_nvram_from_file(a)); \
    }

    NVRAM_DEFAULTS_PATH
#undef FIRMAE_PATH2
#undef FIRMAE_PATH
#undef PATH
#undef NATIVE
#undef TABLE

    // /usr/etc/default in DGN3500-V1.1.00.30_NA.zip
    FILE *file;
    if (firmae_nvram &&
        !access("/firmadyne/nvram_files", R_OK) &&
        (file = fopen("/firmadyne/nvram_files", "r"))) {
        char line[256];
        char *nvram_file;
        char *file_type;
        while (fgets(line, sizeof line, file) != NULL)
        {
            line[strlen(line) - 1] = '\0';
            nvram_file = strtok(line, " ");
            file_type = strtok(NULL, " ");
            file_type = strtok(NULL, " ");

            if (access(nvram_file, R_OK) == -1)
                continue;

            if (strstr(file_type, "ELF") == NULL)
                PRINT_MSG("Loading from default configuration file: %s = %d!\n", nvram_file, parse_nvram_from_file(nvram_file));
        }
    }

    return nvram_set_default_image();
}

static int nvram_set_default_builtin(void) {
    int ret = E_SUCCESS;
    char nvramKeyBuffer[100] = "";
    int index = 0;
    if (!is_load_env) firmae_load_env();

    PRINT_MSG("%s\n", "Setting built-in default values!");

#define ENTRY(a, b, c) \
    if (b(a, c) != E_SUCCESS) { \
        PRINT_MSG("Unable to initialize built-in NVRAM value %s!\n", a); \
        ret = E_FAILURE; \
    }

#define FIRMAE_ENTRY(a, b, c) \
    if (firmae_nvram && b(a, c) != E_SUCCESS) { \
        PRINT_MSG("Unable to initialize built-in NVRAM value %s!\n", a); \
        ret = E_FAILURE; \
    }

#define FIRMAE_FOR_ENTRY(a, b, c, d, e) \
    index = d; \
    if (firmae_nvram) { \
        while (index != e) { \
            snprintf(nvramKeyBuffer, 0x1E, a, index++); \
            ENTRY(nvramKeyBuffer, b, c) \
        } \
    }

    NVRAM_DEFAULTS
#undef FIRMAE_FOR_ENTRY
#undef FIRMAE_ENTRY
#undef ENTRY

    return ret;
}

static int nvram_set_default_image(void) {
    // PRINT_MSG("%s\n", "Copying overrides from defaults folder!");
    // system("/bin/cp "OVERRIDE_POINT"* "MOUNT_POINT);
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
    if (!key) {
        PRINT_MSG("%s\n", "NULL key!");
        return E_FAILURE;
    }
    if (config & 2)
    {
        cache_node* target = get_cached(key, 3);
        if (target != NULL) {
            return E_SUCCESS;
        }
    }    
    int ret = hc(NVRAM_UNSET, &key, 1);
    PRINT_MSG("key = \"%s\", val = \"0x%x\"\n", key, ret);
    return ret;
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
    hc(NVRAM_COMMIT, NULL, 0); 
    return E_SUCCESS;
}

int parse_nvram_from_file(const char *file)
{
    FILE *f;
    char *buffer;
    int fileLen=0;

    if ((f = fopen(file, "rb")) == NULL) {
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

    /* split the buffer including NULL byte */
    #define LEN 1024
    int i = 0, j = 0, k = 0; int left = 1;
    char *key = "", *val = "";
    char larr[LEN] = "", rarr[LEN] = "";

    for(i=0; i < fileLen; i++) {
        char tmp[4];
        sprintf(tmp, "%c", *(buffer + i));

        if (left==1 && j<LEN)
            larr[j++] = tmp[0];
        else if (left == 0 && k < LEN)
            rarr[k++] = tmp[0];

        if (!memcmp(tmp, "=", 1)) {
            left = 0;
            larr[j - 1] = '\0';
        }
        if (!memcmp(tmp, "\x00", 1)) {
            key = larr; val = rarr;
            nvram_set(key, val);
            j = 0; k = 0; left = 1;
            memset(larr, 0, LEN); memset(rarr, 0, LEN);
        }
    }
    return E_SUCCESS;
}
cache_node* get_cached(char* key, int conf) {
    if (cache == NULL || key == NULL) {
        return NULL;
    }
    cache_node* current = cache;
    while (current != NULL) {
        if (strncmp(key, current->key, 0x1000) == 0) {
            if (current->conf & conf) {
                break;
            }
            current = NULL;
            break;
        }
        current = current->forward;
    }
    return current;
}
int delete_cached(char* key) {
    cache_node* target = get_cached(key, 3);
    if (target == NULL) {
        return E_FAILURE;
    }
    if (target == cache_end) {
        cache_end = target->back;
    }
    if (target == cache) {
        cache = target->forward;
    }
    if (target->forward != NULL && target->back != NULL) {
        target->back->forward = target->forward;
        target->forward->back = target->back;
    } else if (target->forward != NULL) {
        target->forward->back = NULL;
    } else if (target->back != NULL) {
        target->back->forward = NULL;
    }
    free(target->key);
    if (target->val) {
        free(target->val);
    }
    free(target);
    return E_SUCCESS;
}
cache_node* create_cache(char* key) {
    cache_node* target;
    if (cache == NULL) {
        cache = malloc(sizeof(cache_node));
        cache->key = strndup(key, BUFFER_SIZE);
        cache_end = cache;
        target = cache;
    } else {
        target = get_cached(key, 3);
        if (target == NULL) {
            target = malloc(sizeof(cache_node));
            target->key = strndup(key, BUFFER_SIZE);
            cache_end->forward = target;
            target->back = cache_end;
            cache_end = target;
        }
        
    }
    return target;
}
void insert_cached_str(char* key, char* val, int conf) {
    cache_node* target = create_cache(key);
    target->val = strndup(val, BUFFER_SIZE);
    target->conf |= conf |1;   
}
void insert_cached_int(char* key, int val, int conf) {
    cache_node* target = create_cache(key);
    target->vali = val;
    target->conf |= conf | 2;   
}
void control(int c) {
    if (c & 1) {
        int sz = BUFFER_SIZE;
        char* key = malloc(sz);
        void** buf = {key, &sz};
        int result = hc(UNSET_CACHE, buf, 2);
        delete_cached(key);
        free(key);        
    }
}

#ifdef FIRMAE_KERNEL
//DIR-615I2, DIR-615I3, DIR-825C1 patch
int VCTGetPortAutoNegSetting(char *a1, int a2) {
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
