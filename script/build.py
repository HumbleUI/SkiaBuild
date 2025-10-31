#! /usr/bin/env python3

import common, os, re, subprocess, sys

def main():
  os.chdir(f'{common.basedir}/skia')

  build_type = common.build_type()
  machine = common.machine()
  system = common.system()
  ndk = common.ndk()

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

  if 'macos' == system:
    args += [
      'skia_use_system_freetype2=false',
      # 'skia_enable_gpu=true',
      'skia_use_metal=true',
      'extra_cflags_cc=["-frtti", "-stdlib=libc++"]'
    ]
    if 'x64' == machine:
      args += ['extra_cflags=["-mmacosx-version-min=10.13"]']
  elif 'linux' == system:
    args += [
      'skia_use_system_freetype2=true',
      # 'skia_enable_gpu=true',
      'extra_cflags_cc=["-frtti"]',
      'skia_use_egl=true',
    ]

    if (machine == 'arm64') and (machine != common.native_machine()):
      args += [
        'cc="aarch64-linux-gnu-gcc-9"',
        'cxx="aarch64-linux-gnu-g++-9"',
        'extra_cflags=["-I/usr/aarch64-linux-gnu/include"]'
      ]
    else:
      args += [
        'cc="gcc-9"',
        'cxx="g++-9"',
      ]

  elif 'windows' == system:
    args += [
      'skia_use_system_freetype2=false',
      # 'skia_use_angle=true',
      'skia_use_direct3d=true',
      'extra_cflags=["-DSK_FONT_HOST_USE_SYSTEM_SETTINGS"]',
    ]
  elif 'android' == system:
    args += [
      'skia_use_system_freetype2=false',
      'ndk="' + ndk + '"'
    ]

  # Generate build instructions
  out = os.path.join('out', build_type + '-' + machine)
  gn = 'gn.exe' if 'windows' == system else 'gn'
  subprocess.check_call([os.path.join('bin', gn), 'gen', out, '--args=' + ' '.join(args)])

  # Compile
  ninja = 'ninja.exe' if 'windows' == system else 'ninja'
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
        f.write(f'  -D{key}\n')
      else:
        f.write(f'  -D{key}={value.replace('\\', '')}\n')
    f.write(')\n')

  return 0

if __name__ == '__main__':
  sys.exit(main())
