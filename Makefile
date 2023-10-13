ARCH ?= x86_64-linux-gnu
BUILD?=$(realpath build)
TARGETS = all
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

clean:
	rm -rf $(BUILD)

all:
	$(MAKE) -C libhypernvram ARCH=$(ARCH) BUILD=$(BUILD) CFLAGS="$(CFLAGS)"
	$(MAKE) -C tests ARCH=$(ARCH) BUILD=$(BUILD) CFLAGS="$(CFLAGS)"
	$(MAKE) -C cli ARCH=$(ARCH) BUILD=$(BUILD) CFLAGS="$(CFLAGS)"
