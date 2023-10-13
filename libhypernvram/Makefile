ARCH ?= x86_64-linux-gnu
BUILD?=.
TARGETS = $(BUILD)/libhypernvram-$(ARCH).so  $(BUILD)/libhypernvram-$(ARCH).a
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

$(BUILD)/libhypernvram-$(ARCH).a: nvram.c
	$(CC) $(CFLAGS) -fpic -c -Wall nvram.c
	$(AR) -rc $(BUILD)/libhypernvram-$(ARCH).a nvram.o

$(BUILD)/libhypernvram-$(ARCH).so: nvram.c
	$(CC) $(CFLAGS) -fPIC -shared -nostdlib $< -o $@

clean:
	rm -f $(TARGETS)
	