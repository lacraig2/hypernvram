#ifndef INCLUDE_NVRAM_H
#define INCLUDE_NVRAM_H


// Sets default NVRAM values using the built-in NVRAM_DEFAULTS table.
static int nvram_set_default_builtin(void);
// Sets default NVRAM values using the override values from OVERRIDE_POINT. Will hold lock.
static int nvram_set_default_image(void);
// Sets default NVRAM values from external table defined in NVRAM_DEFAULTS_PATH.
static int nvram_set_default_table(const char *tbl[]);

/* The following functions form the standard NVRAM API. Functions that return integers
 * will generally return E_SUCCESS/E_FAILURE, with the exception of nvram_get_int(). */

// Initializes NVRAM with default values. Will hold lock.
int nvram_init(void);
// Restores original NVRAM default values.
int nvram_reset(void);
// Clears NVRAM values. Will hold lock.
int nvram_clear(void);
// Pretends to close NVRAM, does nothing.
int nvram_close(void);
// Pretends to commit NVRAM, actually synchronizes file system.
int nvram_commit(void);

// Given a key, gets the corresponding NVRAM value. If key is non-existent, returns NULL.
// Will dynamically allocate memory, so the user should call free().
// On MIPS, will use $a1 as key if $a0 is NULL.
char *nvram_get(const char *key);
// Given a key, gets the corresponding NVRAM value. If key is non-existent, returns "".
// Will dynamically allocate memory.
char *nvram_safe_get(const char *key);
// Given a key, gets the corresponding NVRAM value. If key is non-existent, returns val.
// Otherwise, returns NULL. Will dynamically allocate memory.
char *nvram_default_get_2(const char *key, const char *val);
// Given a key, gets the corresponding NVRAM value into a user-supplied buffer.
// Will hold lock.
int nvram_get_buf(const char *key, char *buf, size_t sz);
// Given a key, gets the corresponding NVRAM value as integer. If key is non-existent, returns E_FAILURE.
// Will hold lock.
int nvram_get_int(const char *key);
// Gets all NVRAM keys and values into a user-supplied buffer, of the format "key=value...".
// Will hold lock.
int nvram_getall(char *buf, size_t len);

// Given a key and value, sets the corresponding NVRAM value. Will hold lock.
int nvram_set(const char *key, const char *val);
// Given a key and value as integer, sets the corresponding NVRAM value. Will hold lock.
int nvram_set_int(const char *key, const int val);
// Given a key, unsets the corresponding NVRAM value. Will hold lock.
int nvram_unset(const char *key);
// Given a key, unset the corresponding NVRAM value if it is set. Will hold lock if it's set
int nvram_safe_unset(const char *key);
// Reloads default NVRAM values.
int nvram_set_default(void);

// Adds a list entry to a NVRAM value.
int nvram_list_add(const char *key, const char *val);
// Checks whether a list entry exists in a NVRAM value. If the magic argument
// is equal to LIST_MAGIC, will either return a pointer to the match or NULL.
char *nvram_list_exist(const char *key, const char *val, int magic);
// Deletes a list entry from a NVRAM value.
int nvram_list_del(const char *key, const char *val);

// Given a key, checks whether the corresponding NVRAM value matches val.
int nvram_match(const char *key, const char *val);
// Given a key, checks whether the corresponding NVRAM value does not match val.
int nvram_invmatch(const char *key, const char *val);

// Parse a default nvram including null byte and passing key,val to nvram_set(JR6150)
int parse_nvram_from_file(const char *file);

#ifdef FIRMAE_KERNEL
int VCTGetPortAutoNegSetting(char *a1, int a2);
// R6200V2, R6250-V1, R6300v2, R6700-V1, R7000-V1 patch infinite loop in httpd
int agApi_fwGetFirstTriggerConf(char *a1);
// R6200V2, R6250-V1, R6300v2, R6700-V1, R7000-V1 patch infinite loop in httpd
int agApi_fwGetNextTriggerConf(char *a1);
#endif

#define MAGIC_VALUE 0x4e564843
#define NVRAM_CLOSE 0x31838180 
#define NVRAM_INIT 0x31838181 
#define NVRAM_CLEAR 0x31838182 
#define NVRAM_LIST_ADD 0x31838183 
#define NVRAM_GET_BUF 0x31838184 
#define NVRAM_GET_INT 0x31838185 
#define NVRAM_GETALL 0x31838186 
#define NVRAM_SET 0x31838187 
#define NVRAM_SET_INT 0x31838188 
#define NVRAM_UNSET 0x31838189 
#define NVRAM_COMMIT 0x3183818a 
#endif
