# Makefile — canonical build for the Sensoray 2600 Windows (x86_64-w64-mingw32) port.
#
# Author   : Maxwell Bloch (github.com/maxwellb)
# Copyright: (C) 2026 Maxwell Bloch
#
# Build from an MSYS2 UCRT64 shell, or run `build.cmd` from a Windows command
# prompt (it launches MSYS2 and invokes this Makefile).
#
# Builds are REPRODUCIBLE: rebuilding the same commit yields byte-identical
# artifacts. See "Reproducibility" below and `make repro`.

CC     := gcc
AR     := ar

COMMON := ../common
BUILD  := build

CFLAGS := -g -Wall -O3 -fno-strict-aliasing
INCS   := -I . -I $(COMMON)

OBJS := $(BUILD)/s26core.o $(BUILD)/s26mod.o

LIB_A  := $(BUILD)/lib2600.a
DLL    := $(BUILD)/s2600.dll
IMPLIB := $(BUILD)/libs2600.dll.a
DEMO   := $(BUILD)/demo.exe

ARTIFACTS := s26core.o s26mod.o lib2600.a s2600.dll libs2600.dll.a demo.exe

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
# Three independent sources of non-determinism had to be eliminated:
#
#   1. PE timestamp. GNU ld writes the link time into the optional header.
#      --no-insert-timestamp writes zero instead, so the clock is irrelevant.
#   2. PE image base. MSYS2's gcc specs enable --enable-auto-image-base, which
#      is not stable across runs here, and the base is baked into the header and
#      into .data relocation entries. Pin it explicitly instead.
#   3. Debug info paths. -g records the build directory, so two checkouts at
#      different paths would differ. -ffile-prefix-map rewrites them to stable
#      placeholders.
#
# Object files and static archives were already deterministic (GCC with
# -frandom-seed, and `ar` in default deterministic/D mode); they are pinned
# explicitly anyway so the guarantee does not depend on toolchain defaults.
#
# SOURCE_DATE_EPOCH is exported for tools that honour it (hatchling uses it for
# wheel timestamps). It defaults to the commit time of HEAD.

FALLBACK_EPOCH := 1762387200

ifeq ($(strip $(SOURCE_DATE_EPOCH)),)
SOURCE_DATE_EPOCH := $(shell git log -1 --format=%ct 2>/dev/null || echo $(FALLBACK_EPOCH))
endif
ifeq ($(strip $(SOURCE_DATE_EPOCH)),)
SOURCE_DATE_EPOCH := $(FALLBACK_EPOCH)
endif
export SOURCE_DATE_EPOCH

# Locale and timezone must not influence output.
export LC_ALL := C
export TZ     := UTC

# Set REPRODUCIBLE=0 to opt out (e.g. to reproduce a historical, timestamped
# build when debugging).
REPRODUCIBLE ?= 1

ifeq ($(REPRODUCIBLE),1)
# Stable placeholders for the two source trees, so debug info does not depend
# on where the repository is checked out.
PATHMAP := -ffile-prefix-map=$(CURDIR)=. \
           -ffile-prefix-map=$(abspath $(COMMON))=/sensoray-common
LDFLAGS_REPRO := -Wl,--no-insert-timestamp
EXE_BASE      := -Wl,--image-base,0x140000000
DLL_BASE      := -Wl,--image-base,0x180000000
else
PATHMAP :=
LDFLAGS_REPRO :=
EXE_BASE      :=
DLL_BASE      :=
endif

CFLAGS += $(PATHMAP)

.PHONY: all lib demo clean repro help

all: lib demo

lib: $(LIB_A) $(DLL)

demo: $(DEMO)

$(BUILD):
	mkdir -p $(BUILD)

# Core (OS-independent, from the SDK's common/ directory). Declare little-endian CPU.
$(BUILD)/s26core.o: $(COMMON)/s26core.c $(COMMON)/app2600.h $(COMMON)/s26modf.h s26mod.h s26app.h | $(BUILD)
	$(CC) $(CFLAGS) -frandom-seed=s26core.c -c -D ENDIAN_LITTLE $(INCS) -o $@ $(COMMON)/s26core.c

# OS-dependent module (Winsock + Win32 threads).
$(BUILD)/s26mod.o: s26mod.c s26mod.h s26app.h $(COMMON)/s26modf.h | $(BUILD)
	$(CC) $(CFLAGS) -frandom-seed=s26mod.c -c $(INCS) -o $@ s26mod.c

# Static library (mirrors the SDK's lib2600.a). `D` forces deterministic mode:
# stable member order and zeroed mtime/uids.
$(LIB_A): $(OBJS)
	$(AR) rcsD $@ $(OBJS)

# Shared library (DLL) for ctypes; also emits the import library $(IMPLIB).
$(DLL): $(OBJS)
	$(CC) -shared -o $@ $(OBJS) -lws2_32 \
		$(DLL_BASE) $(LDFLAGS_REPRO) \
		-Wl,--out-implib,$(IMPLIB) -Wl,--export-all-symbols

# Demo program, linked against the static library.
$(DEMO): demo.c $(LIB_A)
	$(CC) $(CFLAGS) $(INCS) -o $@ demo.c $(LIB_A) -lws2_32 $(EXE_BASE) $(LDFLAGS_REPRO)

clean:
	rm -rf $(BUILD)

# Build twice into separate directories and assert every artifact matches
# byte-for-byte. Fails loudly on the first mismatch.

repro:
	@rm -rf $(BUILD)/repro-a $(BUILD)/repro-b
	@$(MAKE) --no-print-directory BUILD=$(BUILD)/repro-a all >/dev/null
	@$(MAKE) --no-print-directory BUILD=$(BUILD)/repro-b all >/dev/null
	@echo "Reproducibility check (SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH)):"
	@fail=0; for f in $(ARTIFACTS); do \
		if cmp -s $(BUILD)/repro-a/$$f $(BUILD)/repro-b/$$f; then \
			printf '  ok    %s\n' "$$f"; \
		else \
			printf '  FAIL  %s\n' "$$f"; fail=1; \
		fi; \
	done; \
	rm -rf $(BUILD)/repro-a $(BUILD)/repro-b; \
	if [ $$fail -ne 0 ]; then echo "Builds are NOT reproducible."; exit 1; fi; \
	echo "All artifacts reproducible."

help:
	@echo "Targets: all (default), lib, demo, repro, clean"
	@echo "Variables: BUILD=<dir>, REPRODUCIBLE=0|1, SOURCE_DATE_EPOCH=<unix time>"
