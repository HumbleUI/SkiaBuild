#! /usr/bin/env python3

import common, os, re, subprocess, sys, toolchain

# Targets this repo cross compiles to. The GCC cross drivers carry the triple in
# their name; Clang is a single cross compiler and has to be told with --target.
LINUX_TRIPLES = {'arm64': 'aarch64-linux-gnu'}

def gn_string(value):
  for char in '\\"$':
    value = value.replace(char, '\\' + char)
  return '"' + value + '"'

def cc_args(cc, cxx):
  return ['cc=' + gn_string(cc), 'cxx=' + gn_string(cxx)]

def gn_args(build_type, system, machine, native_machine, ndk = '', clang = None):
  '''GN arguments for one build configuration.

  Pure: touches neither the filesystem nor the environment, so every supported
  combination can be exercised by test_gn_args.py. `clang` is a toolchain.Clang
  to build with Clang/LLVM, or None for the platform default compiler (GCC on
  Linux, MSVC on Windows, Apple Clang on macOS, the NDK toolchain on Android).
  '''

  if build_type == 'Debug':
    args = ['is_debug=true']
  else:
    args = ['is_official_build=true']

  args += [
    'target_cpu="' + machine + '"',
    'skia_use_system_expat=false',
    'skia_use_system_libjpeg_turbo=false',
    'skia_use_system_libpng=false',
    'skia_use_system_libwebp=false',
    'skia_use_system_zlib=false',
    # 'skia_use_sfntly=false',
    'skia_use_freetype=true',
    # 'skia_use_harfbuzz=true',
    'skia_use_system_harfbuzz=false',
    'skia_pdf_subset_harfbuzz=true',
    # 'skia_use_icu=true',
    'skia_use_system_icu=false',
    # 'skia_enable_skshaper=true',
    # 'skia_enable_svg=true',
    'skia_enable_skottie=true'
  ]

  extra_cflags = []
  extra_cflags_cc = []

  if 'macos' == system:
    args += [
      'skia_use_system_freetype2=false',
      # 'skia_enable_gpu=true',
      'skia_use_metal=true',
      'skia_use_vulkan=true',
    ]
    extra_cflags_cc += ['-frtti', '-stdlib=libc++']
    if 'x64' == machine:
      extra_cflags += ['-mmacosx-version-min=10.13']
    if clang:
      args += cc_args(clang.cc, clang.cxx)
  elif 'linux' == system:
    args += [
      'skia_use_system_freetype2=true',
      # 'skia_enable_gpu=true',
      'skia_use_egl=true',
      'skia_use_vulkan=true',
    ]
    extra_cflags_cc += ['-frtti']
    cross = 'arm64' == machine and 'arm64' != native_machine
    if cross:
      extra_cflags += ['-I/usr/' + LINUX_TRIPLES[machine] + '/include']
    if clang:
      cc, cxx = clang.cc, clang.cxx
      if cross:
        # The cross GCC installed next to it supplies the sysroot, the C++
        # headers and libstdc++; Clang finds them from the target triple.
        target = ' --target=' + LINUX_TRIPLES[machine]
        cc, cxx = cc + target, cxx + target
      args += cc_args(cc, cxx)
    elif cross:
      args += cc_args(LINUX_TRIPLES[machine] + '-gcc-10', LINUX_TRIPLES[machine] + '-g++-10')
    else:
      args += cc_args('gcc-10', 'g++-10')
  elif 'windows' == system:
    args += [
      'skia_use_system_freetype2=false',
      # 'skia_use_angle=true',
      'skia_use_direct3d=true',
      'skia_use_vulkan=true',
    ]
    extra_cflags += ['-DSK_FONT_HOST_USE_SYSTEM_SETTINGS']
    if clang:
      # Skia keeps its MSVC style toolchain and swaps the compiler and
      # librarian for clang-cl/lld-link when clang_win points at an LLVM root;
      # cc/cxx are not consulted. MSVC and the Windows SDK are still needed for
      # the CRT, the import libraries and the assembler.
      args += ['clang_win=' + gn_string(clang.root.replace('\\', '/'))]
      if clang.resource_version:
        # Skia can work this one out itself, but only milestones from m143 on
        # accept the single component resource directory that Clang 16 and
        # later use ("22" rather than "13.0.1"); older ones fail to configure.
        args += ['clang_win_version=' + gn_string(clang.resource_version)]
  elif 'android' == system:  
    # Built with the toolchain bundled in the NDK, which is Clang already.
    args += [  
        'skia_use_system_freetype2=false',  
        'ndk="' + ndk + '"',  
        'target_os="android"',  
        'skia_use_android_framework=false',  
        'skia_enable_android_utils=true',  
        'skia_use_freetype=true',  
        'skia_use_system_freetype2=false',  
        'skia_use_system_libjpeg_turbo=false',  
        'skia_use_system_libpng=false',  
        'skia_use_system_libwebp=false',  
        'skia_use_system_zlib=false',  
        'skia_use_system_icu=false',  
        'skia_use_expat=true',  
        'skia_use_libjpeg_turbo_encode=true',  
        'skia_use_libjpeg_turbo_decode=true',  
        'skia_use_libpng_encode=true',  
        'skia_use_libpng_decode=true',  
        'skia_use_libwebp_encode=true',  
        'skia_use_libwebp_decode=true',  
        'skia_use_zlib=true',  
        'skia_use_icu=true',  
        'skia_enable_fontmgr_android=true',  
        'skia_enable_skottie=true',  
        'skia_enable_svg=true',  
        'skia_enable_pdf=false',  
        'skia_enable_gpu=true',  
        'skia_use_vulkan=true'  
    ]  
      
    # Android ABI specific settings  
    if machine == 'arm64':  
        args += [  
            'target_cpu="arm64"',  
            'android_abi="arm64-v8a"'  
        ]  
    elif machine == 'x64':  
        args += [  
            'target_cpu="x64"',  
            'android_abi="x86_64"'  
        ]  
      
    # Android API level  
    args += ['android_sdk_api=33']

  if extra_cflags:
    args += ['extra_cflags=[' + ', '.join([gn_string(x) for x in extra_cflags]) + ']']
  if extra_cflags_cc:
    args += ['extra_cflags_cc=[' + ', '.join([gn_string(x) for x in extra_cflags_cc]) + ']']

  return args

def clang_toolchain(system):
  '''The Clang toolchain to build `system` with, or None to use the default.'''
  if not common.use_clang():
    return None

  if 'android' == system:
    print('> --use-clang ignored, the Android NDK toolchain is Clang already', flush = True)
    return None

  clang = toolchain.find_clang(system, common.host_system(), common.clang_path())
  print('> Building with Clang ' + (clang.version or 'of unknown version') + ' from ' + clang.root,
        flush = True)
  if 'macos' == system and not common.clang_path():
    print('> Note: macOS builds use Apple Clang by default, so this changes nothing', flush = True)
  return clang

def main():
  os.chdir(f'{common.basedir}/skia')

  build_type = common.build_type()
  machine = common.machine()
  system = common.system()
  ndk = common.ndk()

  args = gn_args(build_type, system, machine, common.native_machine(), ndk, clang_toolchain(system))

  # Generate build instructions
  out = os.path.join('out', build_type + '-' + machine)
  gn = 'gn.exe' if 'windows' == common.host_system() else 'gn'
  subprocess.check_call([os.path.join('bin', gn), 'gen', out, '--args=' + ' '.join(args)])

  # Compile
  ninja = 'ninja.exe' if 'windows' == common.host_system() else 'ninja'
  subprocess.check_call([os.path.join('third_party/ninja', ninja), '-C', out, 'skia', 'modules'])

  # Extract all unique defines from ninja commands
  ninja_commands = subprocess.check_output([os.path.join('third_party/ninja', ninja), '-C', out, '-t', 'commands'], text=True)
  defines = {}
  for match in re.finditer(r'-D([^ =]+)(?:=(\S+))?', ninja_commands):
    defines[match.group(1)] = match.group(2)
  with open(os.path.join(out, 'defines.cmake'), 'w') as f:
    f.write('add_definitions(\n')
    for key, value in sorted(defines.items()):
      if value is None:
        f.write('  -D' + key + '\n')
      else:
        f.write('  -D' + key + '=' + value.replace('\\', '') + '\n')
    f.write(')\n')

  return 0

if __name__ == '__main__':
  sys.exit(main())
