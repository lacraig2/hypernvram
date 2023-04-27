TARGETLIST=(x86_64-unknown-linux-musl i686-unknown-linux-musl mips-unknown-linux-musl mipsel-unknown-linux-musl arm-unknown-linux-musleabi aarch64-unknown-linux-musl mips64-unknown-linux-muslabi64 mips64el-unknown-linux-muslabi64)
# TARGETLIST=(aarch64-unknown-linux-musl)
# TARGETLIST=(mips-unknown-linux-musl mipsel-unknown-linux-musl)
mkdir -p build
for TARGET in "${TARGETLIST[@]}"; do
    echo "Building for $TARGET"
    mkdir -p build/$TARGET
    CC=/opt/cross/$TARGET/bin/$TARGET-gcc ARCH=$TARGET make
    mv *-$TARGET* build/$TARGET/
done