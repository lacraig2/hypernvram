ARCH ?= x86_64-linux-gnu
BUILD?=.
TARGETS = $(BUILD)/nvram-$(ARCH)
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

$(BUILD)/nvram-$(ARCH): cli.c
	$(CC) $(CFLAGS) -fPIC -static $< -o $@ -L$(BUILD) -lhypernvram-$(ARCH) -I../libhypernvram

clean:
	rm -f $(TARGETS)
	