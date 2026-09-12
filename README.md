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

To build a debug build:

```sh
python3 script/checkout.py --version m91-b99622c05a
python3 script/build.py --build-type Debug
python3 script/archive.py --build-type Debug
```

## Building with Clang

The published Linux and Windows binaries are built with Clang/LLVM -- the
compiler Skia is developed against, and the one its own codegen and warning
settings are written for (Skia's build files are full of `is_clang` branches, and
some dependencies only enable their faster code paths for it). `build.py` still
defaults to the platform compiler, so ask for Clang with `--use-clang`:

```sh
python3 script/checkout.py --version m91-b99622c05a
python3 script/build.py --use-clang
python3 script/archive.py
```

Clang is looked up automatically: on PATH and in the usual installation
directories. Pass `--clang-path <LLVM installation root>` to build with a
specific installation instead. If no usable toolchain is found the build stops
and lists where it looked -- it never falls back to another compiler, so a
build that was asked for Clang is never quietly something else.

What each platform needs:

* **Linux** -- `clang` and `clang++` (`sudo ./script/prepare_linux.sh --with-clang`
  installs them). Cross compiling to arm64 also needs the arm64 GCC cross
  toolchain, which `prepare_linux.sh` installs anyway: Clang compiles for the
  target itself and takes the sysroot, the C++ headers and libstdc++ from there.
* **Windows** -- an LLVM installation, either from the [LLVM
  installer](https://releases.llvm.org) or the "C++ Clang tools for Windows"
  Visual Studio component. MSVC and the Windows SDK are still required: Skia
  only swaps the compiler and librarian for clang-cl and lld-link, and keeps
  using MSVC for the CRT, the SDK libraries and the assembler.
* **macOS** and **Android** are built with Clang already (Apple Clang and the
  toolchain bundled in the NDK), so `--use-clang` changes nothing there unless
  `--clang-path` points at a different LLVM.

CI passes `--use-clang` for every Linux and Windows configuration, so those are
the binaries the releases contain. Artifact names are unchanged: there is one
build per platform and architecture, not a Clang variant alongside another one.

## Running the tests

The GN arguments produced for every supported platform, architecture and
compiler are covered by unit tests. They need neither a Skia checkout nor a
compiler:

```sh
python3 script/test_gn_args.py
```