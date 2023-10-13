#!/bin/bash
TARGETLIST=(x86_64-linux-gnu i686-linux-musl mipseb-linux-musl mipsel-linux-musl arm-linux-musleabi aarch64-linux-musl mips64eb-linux-musl mips64el-linux-musl)
# rm -rf build
mkdir -p build
BUILDDIR=`realpath build`
echo "Built by $USER on $HOSTNAME at `date`" > build/buildinfo.txt
for TARGET in "${TARGETLIST[@]}"; do
    echo "Building for $TARGET"
    CC=$TARGET-gcc ARCH=$TARGET make -j`nproc` -C libhypernvram BUILD=$BUILDDIR all
    CC=$TARGET-gcc ARCH=$TARGET make -j`nproc` -C cli BUILD=$BUILDDIR all
done
