#! /usr/bin/env python3
import common, os, shutil, sys

def main():
  os.chdir(common.basedir)
  shutil.rmtree("skia/out", ignore_errors=True)
  return 0

if __name__ == '__main__':
  sys.exit(main())
