#!/usr/bin/env bash
# Build stock and locally patched ngspice 47 from an existing source checkout.
# Usage: bash tools/build_benchmark_libraries.sh SOURCE_DIRECTORY BUILD_OUTPUT
# Dependencies: C compiler, make, autoconf/automake/libtool, flex, bison, patch.
# Source must be the ngspice-47 tag. This script modifies that disposable source tree.
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo 'Usage: build_benchmark_libraries.sh SOURCE_DIRECTORY BUILD_OUTPUT' >&2
  exit 2
fi
source_tree="$(realpath "$1")"
build_output="$(realpath -m "$2")"
tool_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -e "$build_output" ]; then
  echo 'Build output must be a fresh path.' >&2
  exit 2
fi
mkdir -p "$build_output"
cd "$source_tree"
./autogen.sh > "$build_output/autogen.log" 2>&1
./configure --prefix="$build_output/stock47" --with-ngshared --enable-xspice \
  --enable-klu --disable-debug --without-x --with-readline=no > "$build_output/configure.log" 2>&1
make -j"${SIMCHECK_BUILD_JOBS:-2}" > "$build_output/make-stock.log" 2>&1
make install > "$build_output/install.log" 2>&1
patch -p1 --forward < "$tool_root/third_party/ngspice-47-local-node.patch" > "$build_output/patch.log"
make -j"${SIMCHECK_BUILD_JOBS:-2}" > "$build_output/make-patched.log" 2>&1
mkdir -p "$build_output/patched47/lib"
cp -L src/.libs/libngspice.so "$build_output/patched47/lib/libngspice.so"
python - "$build_output" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
libraries={'ngspice47-stock':str(root/'stock47/lib/libngspice.so'),
           'ngspice47-localpatch':str(root/'patched47/lib/libngspice.so')}
(root/'libraries.json').write_text(json.dumps(libraries,indent=2)+'\n')
print('Ready:',root/'libraries.json')
PY
