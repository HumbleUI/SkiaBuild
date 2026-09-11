#!/bin/bash
set -o errexit -o nounset -o pipefail

apt-get update -y
apt-get install build-essential software-properties-common -y
add-apt-repository ppa:ubuntu-toolchain-r/test -y
apt-get update -y
apt-get install build-essential software-properties-common -y
apt-get update
apt-get install gcc-10 g++-10 gcc-10-aarch64-linux-gnu g++-10-aarch64-linux-gnu -y
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 60 --slave /usr/bin/g++ g++ /usr/bin/g++-10
update-alternatives --config gcc 

apt-get install git python3 wget -y
apt-get install ninja-build fontconfig libfontconfig1-dev libglu1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev curl zip -y

# Clang is only needed by `build.py --use-clang`, so it is opt in and the
# default GCC builds do not pay for it. No linker is installed along with it:
# build.py only ever produces static libraries, so nothing is ever linked.
if [ "${1:-}" = "--with-clang" ]; then
  apt-get install clang -y
fi
