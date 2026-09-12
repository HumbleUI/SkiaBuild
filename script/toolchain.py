#! /usr/bin/env python3

'''Locating a Clang/LLVM toolchain for Skia's GN build.

Skia does not have a single "use clang" switch; how Clang is selected depends on
the target (see skia/gn/BUILDCONFIG.gn and skia/gn/toolchain/BUILD.gn):

  * POSIX targets (Linux, macOS) are compiled with whatever `cc`/`cxx` point at.
    GN sets `is_clang` when those drivers report themselves as Clang, which
    enables Skia's Clang specific warning and codegen flags.
  * Windows targets keep Skia's MSVC style toolchain -- it still needs MSVC and
    the Windows SDK for the CRT headers, the import libraries and ml64.exe --
    and only swap the compiler and librarian for clang-cl/lld-link. That is
    requested by pointing `clang_win` at an LLVM installation root, alongside
    `clang_win_version`. GN can derive the latter itself, but only milestones
    from m143 on recognise the resource directory name Clang 16 and later use,
    which is why this module reports it as `resource_version`.
  * Android is built with the toolchain bundled in the NDK, which is Clang
    already, so there is nothing to locate.

This module only locates a toolchain and reports what it found. Translating that
into GN arguments is build.py's job.
'''

import collections, os, platform, re, shutil, subprocess

# root             LLVM installation root, the directory holding bin/. Needed
#                  for `clang_win` on Windows.
# cc/cxx           absolute paths of the C and C++ drivers.
# version          version reported by the driver, e.g. "18.1.3", or None if
#                  it could not be parsed.
# resource_version name of the resource directory under lib/clang, which is
#                  what GN wants as `clang_win_version`. None when absent.
Clang = collections.namedtuple('Clang', ['root', 'cc', 'cxx', 'version', 'resource_version'],
                               defaults = [None])

class ClangNotFound(Exception):
  pass

def find_clang(target_system, host_system, clang_path = None):
  '''Locate a Clang toolchain able to build target_system on host_system.

  clang_path, when given, is an LLVM installation root (the directory holding
  bin/clang, or bin/clang-cl.exe when targeting Windows) and is used instead of
  searching. Raises ClangNotFound, listing the searched locations, when no
  usable toolchain is available.
  '''
  if 'windows' == target_system:
    return _find_clang_win(host_system, clang_path)
  return _find_clang_posix(host_system, clang_path)

def _exe(name, host_system):
  return name + '.exe' if 'windows' == host_system else name

def _version(driver):
  '''Run the driver, both to validate it and to learn its version.'''
  try:
    out = subprocess.check_output([driver, '--version'], text = True, stderr = subprocess.STDOUT)
  except (OSError, subprocess.CalledProcessError) as e:
    raise ClangNotFound('Could not run "' + driver + ' --version": ' + str(e))
  match = re.search(r'clang version ([0-9]+(?:\.[0-9]+)*)', out)
  return match.group(1) if match else None

def _host_machine():
  machine = platform.machine().lower()
  return {'amd64': 'x64', 'x86_64': 'x64', 'aarch64': 'arm64'}.get(machine, machine)

def _resource_version(root):
  '''Newest directory name under lib/clang, or None.

  Clang keeps its builtin headers and runtime libraries in lib/clang/<version>.
  Clang 15 and earlier named it "13.0.1", Clang 16 and later name it "22".
  '''
  try:
    entries = os.listdir(os.path.join(root, 'lib', 'clang'))
  except OSError:
    return None
  versions = [x for x in entries if re.match(r'^[0-9]+(\.[0-9]+)*$', x)]
  if not versions:
    return None
  return max(versions, key = lambda x: [int(part) for part in x.split('.')])

### Windows: clang-cl + lld-link, addressed by installation root

def _windows_roots(host_system):
  '''Candidate LLVM installation roots, most explicit first.'''
  roots = []

  # LLVM on PATH is the most direct statement of intent.
  clang_cl = shutil.which(_exe('clang-cl', host_system))
  if clang_cl:
    roots.append(os.path.dirname(os.path.dirname(os.path.realpath(clang_cl))))

  # Where the LLVM installer puts it.
  for var in ['ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)']:
    base = os.environ.get(var)
    if base:
      roots.append(os.path.join(base, 'LLVM'))

  # The "C++ Clang tools for Windows" Visual Studio component. VCINSTALLDIR is
  # exported by vcvarsall.bat, which CI runs before building.
  vc = os.environ.get('VCINSTALLDIR')
  if vc:
    cpus = ['ARM64', 'x64'] if 'arm64' == _host_machine() else ['x64', 'ARM64']
    roots += [os.path.join(vc, 'Tools', 'Llvm', cpu) for cpu in cpus]

  # ProgramFiles and ProgramW6432 are the same directory on 64 bit Windows.
  return list(dict.fromkeys(roots))

def _find_clang_win(host_system, clang_path):
  roots = [clang_path] if clang_path else _windows_roots(host_system)
  clang_cl = _exe('clang-cl', host_system)
  lld_link = _exe('lld-link', host_system)

  for root in roots:
    driver = os.path.join(root, 'bin', clang_cl)
    if os.path.isfile(driver) and os.path.isfile(os.path.join(root, 'bin', lld_link)):
      return Clang(root = os.path.abspath(root),
                   cc = driver,
                   cxx = os.path.join(root, 'bin', _exe('clang++', host_system)),
                   version = _version(driver),
                   resource_version = _resource_version(root))

  raise ClangNotFound(
    'Could not find an LLVM installation with bin/' + clang_cl + ' and bin/' + lld_link + '.\n'
    'Looked in:\n  ' + '\n  '.join(roots or ['<nothing on PATH>']) + '\n'
    'Install LLVM (https://releases.llvm.org) or the "C++ Clang tools for Windows"\n'
    'Visual Studio component, or pass --clang-path <LLVM installation root>.')

### POSIX: clang/clang++ drivers, addressed by path

def _find_clang_posix(host_system, clang_path):
  clang = _exe('clang', host_system)
  clangxx = _exe('clang++', host_system)

  if clang_path:
    cc = os.path.join(clang_path, 'bin', clang)
    cxx = os.path.join(clang_path, 'bin', clangxx)
  else:
    # Whatever the machine is configured to use: update-alternatives, Xcode, a
    # toolchain on PATH. An installation that only provides versioned drivers,
    # as apt.llvm.org does, is selected with --clang-path.
    cc, cxx = shutil.which(clang), shutil.which(clangxx)

  if cc and cxx and os.path.isfile(cc) and os.path.isfile(cxx):
    cc, cxx = os.path.realpath(cc), os.path.realpath(cxx)
    return Clang(root = os.path.dirname(os.path.dirname(cc)),
                 cc = cc,
                 cxx = cxx,
                 version = _version(cc))

  raise ClangNotFound(
    'Could not find ' + clang + ' and ' + clangxx +
    (' in "' + os.path.join(clang_path, 'bin') + '"' if clang_path else ' on PATH') + '.\n'
    'Install Clang ("script/prepare_linux.sh --with-clang" on Debian/Ubuntu, the\n'
    'Xcode command line tools on macOS) or pass --clang-path <LLVM installation root>.')
