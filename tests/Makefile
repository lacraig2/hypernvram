ARCH ?= x86_64-linux-gnu
BUILD?=.
TARGETS = $(BUILD)/hc_test-$(ARCH)  $(BUILD)/nvram_test-$(ARCH)
CFLAGS ?= -g

.PHONY: all clean

all: $(TARGETS)

$(BUILD)/hc_test-$(ARCH): hc_test.c
	$(CC) $(CFLAGS) -fPIC -static $< -o $@  -I../include

$(BUILD)/nvram_test-$(ARCH): nvram_test.c
	$(CC) $(CFLAGS) -fPIC -static $< -o $@ -L$(BUILD) -lhypernvram-$(ARCH) -I../include

clean:
	rm -f $(TARGETS)
	