ARCH ?= x86_64
TARGETS = libnvram-$(ARCH).so cli_example-$(ARCH) hc_test-$(ARCH)
CFLAGS ?= -g

.PHONY: all clean

ifeq ($(ARCH),mipsel-unknown-linux-musl)
CFLAGS += -mips32r3
else ifeq ($(ARCH),mips-unknown-linux-musl)
CFLAGS += -mips32r3
else ifeq ($(ARCH),mips64-unknown-linux-muslabi64)
CFLAGS += -mips64r2
else ifeq ($(ARCH),mips64el-unknown-linux-muslabi64)
CFLAGS += -mips64r2
endif

all: $(TARGETS)

libnvram-$(ARCH).so: nvram.c
	$(CC) $(CFLAGS) -fPIC -shared -nostdlib $< -o $@

hc_test-$(ARCH): hc_test.c
	$(CC) $(CFLAGS) -static $< -o $@

cli_example-$(ARCH): cli_example.c
	$(CC) $(CFLAGS) -L. -lnvram-$(ARCH) $< -o $@

clean:
	rm -f $(TARGETS)