#! /usr/bin/env python3

import argparse, common, os, pathlib, platform, re, subprocess, sys

def main():
  os.chdir(os.path.join(os.path.dirname(__file__), os.pardir))
  
  parser = common.create_parser(True)
  args = parser.parse_args()

  # Clone Skia
  match = re.match('(m\\d+)(?:-([0-9a-f]+)(?:-([1-9][0-9]*))?)?', args.version)
  if not match:
    raise Exception('Expected --version "m<ver>-<sha>", got "' + args.version + '"')
  branch = "chrome/" + match.group(1)
  commit = match.group(2)
  iteration = match.group(3)

  if os.path.exists("skia"):
    os.chdir("skia")
    if subprocess.check_output(["git", "branch", "--list", branch]):
      print("> Advancing", branch)
      subprocess.check_call(["git", "checkout", "-B", branch])
      subprocess.check_call(["git", "fetch"])
      subprocess.check_call(["git", "reset", "--hard", "origin/" + branch])
    else:
      print("> Fetching", branch)
      subprocess.check_call(["git", "reset", "--hard"])
      subprocess.check_call(["git", "fetch", "origin", branch + ":remotes/origin/" + branch])
      subprocess.check_call(["git", "checkout", branch])
  else:
    print("> Cloning", branch)
    subprocess.check_call(["git", "clone", "https://skia.googlesource.com/skia", "--quiet", "--branch", branch, "skia"])
    os.chdir("skia")

  # Checkout commit
  print("> Checking out", commit)
  subprocess.check_call(["git", "-c", "advice.detachedHead=false", "checkout", commit])

  # Apply patches
  subprocess.check_call(["git", "reset", "--hard"])
  for x in pathlib.Path(os.pardir, 'patches').glob('*.patch'):
    print("> Applying", x)
    subprocess.check_call(["git", "apply", str(x)])

  # git deps
  env = os.environ.copy()
  if 'windows' == common.system():
    env['PYTHONHTTPSVERIFY']='0'

  subprocess.check_call(["python3", "tools/git-sync-deps"], env=env)
  subprocess.check_call(["python3", "bin/fetch-gn"], env=env)
  subprocess.check_call(["python3", "bin/fetch-ninja"], env=env)

  return 0

if __name__ == '__main__':
  sys.exit(main())
