ARCH ?= x86_64-linux-gnu
BUILD?=.
TARGETS = $(BUILD)/nvram-$(ARCH)
CFLAGS ?= -g

.PHONY: all clean

all: $(TARGETS)

$(BUILD)/nvram-$(ARCH): cli.c
	$(CC) $(CFLAGS) -fPIC -static $< -o $@ -L$(BUILD) -lhypernvram-$(ARCH) -I../libhypernvram

clean:
	rm -f $(TARGETS)
	