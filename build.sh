#!/bin/bash
TARGETLIST=(x86_64-linux-gnu i686-linux-musl mipseb-linux-musl mipsel-linux-musl arm-linux-musleabi aarch64-linux-musl mips64eb-linux-musl mips64el-linux-musl)
mkdir -p build
echo "Built by $USER on $HOSTNAME at `date`" > build/buildinfo.txt
for TARGET in "${TARGETLIST[@]}"; do
    echo "Building for $TARGET"
    mkdir -p build/
    CC=$TARGET-gcc ARCH=$TARGET make -j`nproc`
    mv *-$TARGET* build
done