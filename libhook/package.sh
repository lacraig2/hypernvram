#!/bin/bash
set -eux

echo "Building for 3 target arches"
cargo build --target arm-unknown-linux-gnueabi --release
cargo build --target mips-unknown-linux-gnu --release
cargo build --target mipsel-unknown-linux-gnu --release


OUT=bundle
echo "Packaging into ${OUT} and packaging as vpn.tar.gz"
rm  -rf $OUT
mkdir -p $OUT

echo "libhook at $(git rev-parse HEAD) built at $(date)" > $OUT/README.txt

for x in $(ls ./target/*/release/liblibhook.so); do 
  echo ${x}
  ARCH=$(basename $(dirname $(dirname $x)))
  cp $x ${OUT}/libhook.${ARCH}.so
done

tar cvfz libhook.tar.gz bundle/
