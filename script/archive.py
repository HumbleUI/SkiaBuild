#! /usr/bin/env python3

import common, os, pathlib, sys, zipfile

def parents(path):
  res = []
  parent = path.parent
  while '.' != str(parent):
    res.insert(0, parent)
    parent = parent.parent
  return res

def main():
  os.chdir(os.path.join(os.path.dirname(__file__), os.pardir, 'skia'))
  
  build_type = common.build_type()
  version = common.version()
  machine = common.machine()
  system = common.system()
  classifier = common.classifier()

  globs = [
    'out/' + build_type + '-' + machine + '/*.a',
    'out/' + build_type + '-' + machine + '/*.lib',
    'out/' + build_type + '-' + machine + '/icudtl.dat',
    'out/' + build_type + '-' + machine + '/defines.cmake',
    'include/**/*',
    'modules/particles/**/*.h',
    'modules/skcms/**/*.h',
    'modules/skottie/**/*.h',
    'modules/skparagraph/**/*.h',
    'modules/skplaintexteditor/**/*.h',
    'modules/skresources/**/*.h',
    'modules/sksg/**/*.h',
    'modules/skshaper/**/*.h',
    'modules/skunicode/**/*.h',
    'modules/svg/**/*.h',
    'src/**/*.h',
    'third_party/externals/angle2/LICENSE',
    'third_party/externals/angle2/include/**/*',
    'third_party/externals/freetype/docs/FTL.TXT',
    'third_party/externals/freetype/docs/GPLv2.TXT',
    'third_party/externals/freetype/docs/LICENSE.TXT',
    'third_party/externals/freetype/include/**/*',
    'third_party/externals/icu/source/common/**/*.h',
    'third_party/externals/libpng/LICENSE',
    'third_party/externals/libpng/*.h',
    'third_party/externals/libwebp/COPYING',
    'third_party/externals/libwebp/PATENTS',
    'third_party/externals/libwebp/src/dec/*.h',
    'third_party/externals/libwebp/src/dsp/*.h',
    'third_party/externals/libwebp/src/enc/*.h',
    'third_party/externals/libwebp/src/mux/*.h',
    'third_party/externals/libwebp/src/utils/*.h',
    'third_party/externals/libwebp/src/webp/*.h',
    'third_party/externals/harfbuzz/COPYING',
    'third_party/externals/harfbuzz/src/*.h',
    'third_party/externals/swiftshader/LICENSE.txt',
    'third_party/externals/swiftshader/include/**/*',
    'third_party/externals/zlib/LICENSE',
    'third_party/externals/zlib/*.h',
    "third_party/icu/*.h"
  ]

  target = 'Skia-' + version + '-' + system + '-' + build_type + '-' + machine + classifier + '.zip'
  print('> Writing', target)
  
  with zipfile.ZipFile(os.path.join(os.pardir, target), 'w', compression=zipfile.ZIP_DEFLATED) as zip:
    dirs = set()
    for glob in globs:
      for path in pathlib.Path().glob(glob):
        if not path.is_dir():
          for dir in parents(path):
            if not dir in dirs:
              zip.write(str(dir))
              dirs.add(dir)
          zip.write(str(path))

  return 0

if __name__ == '__main__':
  sys.exit(main())
