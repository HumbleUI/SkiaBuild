#! /usr/bin/env python3

'''Unit tests for the GN argument generation in build.py.

Run with `python3 script/test_gn_args.py`. They need neither a Skia checkout nor
a compiler, so every supported platform/architecture/compiler combination can be
checked anywhere, including on CI machines that only build one of them.
'''

import itertools, os, shutil, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build, common, toolchain

SYSTEMS = ['macos', 'linux', 'windows', 'android']
MACHINES = ['x64', 'arm64']
BUILD_TYPES = ['Release', 'Debug']

CLANG_POSIX = toolchain.Clang(
  root = '/usr/lib/llvm-18',
  cc = '/usr/lib/llvm-18/bin/clang',
  cxx = '/usr/lib/llvm-18/bin/clang++',
  version = '18.1.3')

CLANG_WIN = toolchain.Clang(
  root = 'C:\\Program Files\\LLVM',
  cc = 'C:\\Program Files\\LLVM\\bin\\clang-cl.exe',
  cxx = 'C:\\Program Files\\LLVM\\bin\\clang++.exe',
  version = '18.1.3',
  resource_version = '18')

def every_configuration():
  for system, machine, build_type, native_machine in itertools.product(
      SYSTEMS, MACHINES, BUILD_TYPES, MACHINES):
    for clang in [None, CLANG_WIN if 'windows' == system else CLANG_POSIX]:
      yield (build_type, system, machine, native_machine, clang)

def args_for(build_type, system, machine, native_machine, clang):
  return build.gn_args(build_type, system, machine, native_machine, '/opt/ndk', clang)

class TestBackwardsCompatibility(unittest.TestCase):
  '''The default compiler of every platform must keep producing what it did
  before Clang support was added.'''

  def test_linux_arm64_cross_gcc(self):
    self.assertEqual(args_for('Release', 'linux', 'arm64', 'x64', None), [
      'is_official_build=true',
      'target_cpu="arm64"',
      'skia_use_system_expat=false',
      'skia_use_system_libjpeg_turbo=false',
      'skia_use_system_libpng=false',
      'skia_use_system_libwebp=false',
      'skia_use_system_zlib=false',
      'skia_use_freetype=true',
      'skia_use_system_harfbuzz=false',
      'skia_pdf_subset_harfbuzz=true',
      'skia_use_system_icu=false',
      'skia_enable_skottie=true',
      'skia_use_system_freetype2=true',
      'skia_use_egl=true',
      'skia_use_vulkan=true',
      'cc="aarch64-linux-gnu-gcc-10"',
      'cxx="aarch64-linux-gnu-g++-10"',
      'extra_cflags=["-I/usr/aarch64-linux-gnu/include"]',
      'extra_cflags_cc=["-frtti"]',
    ])

  def test_linux_native_gcc(self):
    args = args_for('Release', 'linux', 'x64', 'x64', None)
    self.assertIn('cc="gcc-10"', args)
    self.assertIn('cxx="g++-10"', args)
    self.assertIn('extra_cflags_cc=["-frtti"]', args)
    self.assertNotIn('extra_cflags=["-I/usr/aarch64-linux-gnu/include"]', args)

  def test_windows_msvc(self):
    self.assertEqual(args_for('Release', 'windows', 'x64', 'x64', None), [
      'is_official_build=true',
      'target_cpu="x64"',
      'skia_use_system_expat=false',
      'skia_use_system_libjpeg_turbo=false',
      'skia_use_system_libpng=false',
      'skia_use_system_libwebp=false',
      'skia_use_system_zlib=false',
      'skia_use_freetype=true',
      'skia_use_system_harfbuzz=false',
      'skia_pdf_subset_harfbuzz=true',
      'skia_use_system_icu=false',
      'skia_enable_skottie=true',
      'skia_use_system_freetype2=false',
      'skia_use_direct3d=true',
      'skia_use_vulkan=true',
      'extra_cflags=["-DSK_FONT_HOST_USE_SYSTEM_SETTINGS"]',
    ])

  def test_macos_defaults(self):
    args = args_for('Debug', 'macos', 'x64', 'x64', None)
    self.assertIn('is_debug=true', args)
    self.assertIn('skia_use_metal=true', args)
    self.assertIn('extra_cflags=["-mmacosx-version-min=10.13"]', args)
    self.assertIn('extra_cflags_cc=["-frtti", "-stdlib=libc++"]', args)
    # The deployment target is x64 only.
    self.assertNotIn('extra_cflags=["-mmacosx-version-min=10.13"]',
                     args_for('Debug', 'macos', 'arm64', 'arm64', None))

  def test_android_defaults(self):
    args = args_for('Release', 'android', 'arm64', 'x64', None)
    self.assertIn('ndk="/opt/ndk"', args)
    self.assertIn('target_os="android"', args)
    self.assertIn('android_abi="arm64-v8a"', args)
    self.assertIn('android_sdk_api=33', args)
    self.assertIn('android_abi="x86_64"', args_for('Release', 'android', 'x64', 'x64', None))

class TestClang(unittest.TestCase):

  def test_linux_uses_clang_drivers(self):
    args = args_for('Release', 'linux', 'x64', 'x64', CLANG_POSIX)
    self.assertIn('cc="/usr/lib/llvm-18/bin/clang"', args)
    self.assertIn('cxx="/usr/lib/llvm-18/bin/clang++"', args)
    self.assertNotIn('cc="gcc-10"', args)

  def test_linux_cross_passes_target_triple(self):
    '''Clang is a single cross compiler: the triple is what selects the target.
    CLangV4 dropped Clang entirely for cross builds and silently used GCC.'''
    args = args_for('Release', 'linux', 'arm64', 'x64', CLANG_POSIX)
    self.assertIn('cc="/usr/lib/llvm-18/bin/clang --target=aarch64-linux-gnu"', args)
    self.assertIn('cxx="/usr/lib/llvm-18/bin/clang++ --target=aarch64-linux-gnu"', args)
    self.assertIn('extra_cflags=["-I/usr/aarch64-linux-gnu/include"]', args)

  def test_linux_native_arm64_is_not_cross(self):
    args = args_for('Release', 'linux', 'arm64', 'arm64', CLANG_POSIX)
    self.assertIn('cc="/usr/lib/llvm-18/bin/clang"', args)

  def test_windows_sets_clang_win_only(self):
    '''Skia keeps its MSVC style toolchain on Windows and picks clang-cl/lld-link
    from clang_win; cc/cxx are never consulted there.'''
    args = args_for('Release', 'windows', 'x64', 'x64', CLANG_WIN)
    self.assertIn('clang_win="C:/Program Files/LLVM"', args)
    self.assertFalse([x for x in args if x.startswith('cc=') or x.startswith('cxx=')])

  def test_windows_pins_the_resource_directory(self):
    '''Skia milestones before m143 only match a three component resource
    directory name, so Clang 16+ would fail to configure without this.'''
    args = args_for('Release', 'windows', 'x64', 'x64', CLANG_WIN)
    self.assertIn('clang_win_version="18"', args)
    without = CLANG_WIN._replace(resource_version = None)
    self.assertFalse([x for x in args_for('Release', 'windows', 'x64', 'x64', without)
                      if x.startswith('clang_win_version=')])

  def test_windows_arm64_is_supported(self):
    '''Skia adds --target=arm64-windows itself, so nothing extra is needed and
    there is no reason to fall back to MSVC.'''
    self.assertIn('clang_win="C:/Program Files/LLVM"',
                  args_for('Release', 'windows', 'arm64', 'arm64', CLANG_WIN))

  def test_macos_pins_the_drivers(self):
    args = args_for('Release', 'macos', 'arm64', 'arm64', CLANG_POSIX)
    self.assertIn('cc="/usr/lib/llvm-18/bin/clang"', args)
    self.assertIn('extra_cflags_cc=["-frtti", "-stdlib=libc++"]', args)

  def test_android_ignores_clang(self):
    '''The NDK toolchain is Clang already; overriding cc/cxx would break it.'''
    self.assertEqual(args_for('Release', 'android', 'arm64', 'x64', CLANG_POSIX),
                     args_for('Release', 'android', 'arm64', 'x64', None))

class TestInvariants(unittest.TestCase):
  '''Checked for every platform, architecture, build type and compiler.'''

  def test_every_argument_is_an_assignment(self):
    for config in every_configuration():
      for arg in args_for(*config):
        self.assertRegex(arg, r'^[a-z_][a-z0-9_]*=\S', msg = str(config))

  def test_no_argument_gets_two_values(self):
    '''GN takes the last assignment, so an argument built up in two places (as
    extra_cflags used to be) would silently lose half of its content. Repeating
    an argument with the same value is harmless and the Android block does it.'''
    for config in every_configuration():
      values = {}
      for arg in args_for(*config):
        name, value = arg.split('=', 1)
        self.assertEqual(values.setdefault(name, value), value,
                         msg = str(config) + ': conflicting values for ' + name)

  def test_target_cpu_always_matches_the_requested_machine(self):
    for config in every_configuration():
      machine = config[2]
      self.assertIn('target_cpu="' + machine + '"', args_for(*config), msg = str(config))

  def test_build_type_selects_debug_or_official(self):
    for config in every_configuration():
      args = args_for(*config)
      if 'Debug' == config[0]:
        self.assertIn('is_debug=true', args)
        self.assertNotIn('is_official_build=true', args)
      else:
        self.assertIn('is_official_build=true', args)
        self.assertNotIn('is_debug=true', args)

class TestQuoting(unittest.TestCase):

  def test_gn_string_escapes(self):
    self.assertEqual(build.gn_string('clang'), '"clang"')
    self.assertEqual(build.gn_string('C:\\LLVM'), '"C:\\\\LLVM"')
    self.assertEqual(build.gn_string('a"b'), '"a\\"b"')

  def test_paths_with_spaces_stay_one_gn_token(self):
    args = args_for('Release', 'windows', 'x64', 'x64', CLANG_WIN)
    clang_win = [x for x in args if x.startswith('clang_win=')][0]
    self.assertEqual(clang_win.count('"'), 2)

class TestClangDiscovery(unittest.TestCase):
  '''Covers the lookup helpers in toolchain.py. They are driven with fabricated
  directories so the POSIX layouts can be checked on any host; the parts that
  execute a driver need a real Clang and are left to the build itself.'''

  def setUp(self):
    self.dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.dir, True)

  def touch(self, *parts):
    path = os.path.join(self.dir, *parts)
    os.makedirs(os.path.dirname(path), exist_ok = True)
    open(path, 'w').close()
    return path

  def test_versioned_drivers_prefer_the_newest(self):
    for version in ['9', '14', '18']:
      self.touch('bin', 'clang-' + version)
      self.touch('bin', 'clang++-' + version)
    # A driver without its C++ counterpart is not a usable pair.
    self.touch('bin', 'clang-20')
    path = os.environ['PATH']
    self.addCleanup(os.environ.__setitem__, 'PATH', path)
    os.environ['PATH'] = os.path.join(self.dir, 'bin')
    found = toolchain._versioned_drivers('linux')
    self.assertEqual([os.path.basename(cc) for cc, _ in found],
                     ['clang-18', 'clang-14', 'clang-9'])
    self.assertTrue(found[0][1].endswith('clang++-18'))

  def test_resource_version_handles_both_namings(self):
    self.assertIsNone(toolchain._resource_version(self.dir))
    os.makedirs(os.path.join(self.dir, 'lib', 'clang', '13.0.1'))
    self.assertEqual(toolchain._resource_version(self.dir), '13.0.1')
    # Clang 16+ uses the bare major version, which sorts before "13.0.1" as text.
    os.makedirs(os.path.join(self.dir, 'lib', 'clang', '22'))
    self.assertEqual(toolchain._resource_version(self.dir), '22')

  def test_windows_lookup_reports_where_it_looked(self):
    with self.assertRaises(toolchain.ClangNotFound) as caught:
      toolchain.find_clang('windows', 'windows', os.path.join(self.dir, 'llvm'))
    self.assertIn('clang-cl.exe', str(caught.exception))
    self.assertIn(os.path.join(self.dir, 'llvm'), str(caught.exception))

  def test_posix_lookup_reports_where_it_looked(self):
    with self.assertRaises(toolchain.ClangNotFound) as caught:
      toolchain.find_clang('linux', 'linux', os.path.join(self.dir, 'llvm'))
    self.assertIn(os.path.join(self.dir, 'llvm', 'bin'), str(caught.exception))

  def test_driver_names_follow_the_host_not_the_target(self):
    '''Skia can build a Windows target from a POSIX host, where the LLVM tools
    have no .exe suffix.'''
    self.assertEqual(toolchain._exe('clang-cl', 'windows'), 'clang-cl.exe')
    self.assertEqual(toolchain._exe('clang-cl', 'linux'), 'clang-cl')

class TestArgumentParsing(unittest.TestCase):
  '''--use-clang is fed straight from a GitHub Actions expression, which expands
  to "true", "false" or, on a push, to nothing at all.'''

  def test_accepted_values(self):
    for value in ['true', 'True', 'TRUE', ' yes ', 'on', '1']:
      self.assertTrue(common.parse_bool('--use-clang', value), msg = value)
    for value in ['false', 'False', 'no', 'off', '0', '', '  ']:
      self.assertFalse(common.parse_bool('--use-clang', value), msg = value)

  def test_rejects_garbage(self):
    with self.assertRaises(Exception):
      common.parse_bool('--use-clang', 'clang')

  def test_flag_forms(self):
    parser = common.create_parser()
    self.assertEqual(parser.parse_known_args([])[0].use_clang, 'false')
    self.assertEqual(parser.parse_known_args(['--use-clang'])[0].use_clang, 'true')
    self.assertEqual(parser.parse_known_args(['--use-clang', 'true'])[0].use_clang, 'true')
    self.assertEqual(parser.parse_known_args(['--use-clang', ''])[0].use_clang, '')
    # A bare --use-clang must not swallow the next option.
    (args, _) = parser.parse_known_args(['--use-clang', '--machine', 'x64'])
    self.assertEqual(args.use_clang, 'true')
    self.assertEqual(args.machine, 'x64')

if __name__ == '__main__':
  unittest.main()
