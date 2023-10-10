ARCH ?= x86_64
TARGETS = libnvram-$(ARCH).so 
#cli_example-$(ARCH) hc_test-$(ARCH)
CFLAGS ?= -g

.PHONY: all clean

ifeq ($(ARCH),mipsel-linux-musl)
CFLAGS += -mips32r3
else ifeq ($(ARCH),mipseb-linux-musl)
CFLAGS += -mips32r3
else ifeq ($(ARCH),mips64eb-linux-musl)
CFLAGS += -mips64r2
else ifeq ($(ARCH),mips64el-linux-musl)
CFLAGS += -mips64r2
endif

all: $(TARGETS)

libnvram-$(ARCH).so: nvram.c
	$(CC) $(CFLAGS) -fPIC -shared -nostdlib $< -o $@

# hc_test-$(ARCH): hc_test.c
	# $(CC) $(CFLAGS) -static $< -o $@

# cli_example-$(ARCH): cli_example.c
	# $(CC) $(CFLAGS) -L. -lnvram-$(ARCH) $< -o $@

clean:
	rm -f $(TARGETS)