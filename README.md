# Automated Skia builds

This repo is dedicated to building Skia binaries for use in [Skija](https://github.com/HumbleUI/Skija).

## Prebuilt binaries

Prebuilt binaries can be found [in releases](https://github.com/HumbleUI/SkiaBuild/releases).

## Building next version of Skia

Update `version` in [.github/workflows/build.yml](https://github.com/HumbleUI/SkiaBuild/blob/master/.github/workflows/build.yml).

## Building locally

```sh
python3 script/checkout.py --version m91-b99622c05a
python3 script/build.py
python3 script/archive.py
```

Linux and Windows are built with Clang/LLVM; macOS and Android use the Clang
that comes with Xcode and the NDK. `script/prepare_linux.sh` installs it on
Linux. On Windows an LLVM installation is expected in `C:\Program Files\LLVM`,
next to MSVC and the Windows SDK, which Skia still needs for the CRT, the import
libraries and the assembler.

To build a debug build:

```sh
python3 script/checkout.py --version m91-b99622c05a
python3 script/build.py --build-type Debug
python3 script/archive.py --build-type Debug
```