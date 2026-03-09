GBDK_HOME ?= /opt/gbdk
LCC       := $(GBDK_HOME)/bin/lcc

CFLAGS    := -Wa-l -Wl-m -Wl-j
ROMFLAGS  := -Wm-yc -Wm-yt1 -Wm-yn"WSTLND RACER"

TARGET    := build/wasteland-racer.gb
OBJ_DIR   := build/obj

SRCS      := $(wildcard src/*.c)
OBJS      := $(patsubst src/%.c,$(OBJ_DIR)/%.o,$(SRCS))

.PHONY: all clean

all: $(TARGET)

$(OBJ_DIR)/%.o: src/%.c | $(OBJ_DIR)
	$(LCC) $(CFLAGS) $(ROMFLAGS) -c -o $@ $<

$(TARGET): $(OBJS) | build
	$(LCC) $(CFLAGS) $(ROMFLAGS) -o $@ $(OBJS)

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

build:
	mkdir -p build

clean:
	rm -rf build/
