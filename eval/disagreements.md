# Gemini says infra, label says regression (30 cases)

From `results_small.md` (model `gemini-3.5-flash-lite`). Random sample, seed 0: up to 15 regression_strong + 15 regression_weak test incidents where Gemini answered infra.
For each case fill in the verdict: label correct / Gemini correct / unclear.

## 1. apache/arrow · regression_strong

- incident `9fe324ff324c` · 2026-10-21 08:56 UTC · 2 job(s) · https://github.com/apache/arrow/actions/runs/39573045848/job/119131700320
- job: `ARM64 macOS 14 C++`
- failed steps: Test
- Gemini likely_cause: The test timed out on the ARM64 macOS runner, which is characteristic of an infrastructure performance issue or job timeout.
- fix commit(s):
- https://github.com/apache/arrow/commit/42431073435080acc0f06642dd2ad183885ae4fd (fix run https://github.com/apache/arrow/actions/runs/39586200385)
- https://github.com/apache/arrow/commit/be36e4fcac4b344c6ebdf2ad2558e16ab514dcd9 (fix run https://github.com/apache/arrow/actions/runs/39579254721)
- touched files: cpp/src/arrow/flight/CMakeLists.txt, cpp/src/arrow/flight/flight_internals_test.cc, cpp/src/arrow/flight/flight_test.cc, cpp/src/arrow/flight/meson.build, cpp/src/arrow/flight/server.cc, cpp/src/arrow/flight/server.h, cpp/src/arrow/flight/server_tracing_middleware.cc, cpp/src/arrow/flight/transport/grpc/grpc_server.cc, cpp/src/arrow/flight/transport/grpc/grpc_server_internal.cc, cpp/src/arrow/flight/transport/grpc/grpc_server_internal.h

Failure region (last 25 normalized lines):

```
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
<n>% tests passed, <n> tests failed out of <n>
label time summary:
arrow-compute-tests = <n>.<n> sec*proc (<n> tests)
arrow-tests = <n>.<n> sec*proc (<n> tests)
arrow_acero = <n>.<n> sec*proc (<n> tests)
arrow_dataset = <n>.<n> sec*proc (<n> tests)
arrow_flight = <n>.<n> sec*proc (<n> tests)
arrow_substrait = <n>.<n> sec*proc (<n> test)
filesystem = <n>.<n> sec*proc (<n> tests)
gandiva-tests = <n>.<n> sec*proc (<n> tests)
parquet-tests = <n>.<n> sec*proc (<n> tests)
unittest = <n>.<n> sec*proc (<n> tests)
total test time (real) = <n>.<n> sec
the following tests failed:
<n> - arrow-s<n>fs-test (timeout) arrow-tests filesystem unittest
errors while running ctest
process completed with exit code <n>.
```

**verdict: ___**

## 2. apache/arrow · regression_strong

- incident `ef216680b8e7` · 2026-10-21 09:44 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39579254421/job/119152472360
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: Homebrew dependency resolution failed to find the requested llvm formula version on the macOS runner environment.
- fix commit(s):
- https://github.com/apache/arrow/commit/42431073435080acc0f06642dd2ad183885ae4fd (fix run https://github.com/apache/arrow/actions/runs/39586199846)
- touched files: cpp/src/arrow/flight/CMakeLists.txt, cpp/src/arrow/flight/flight_internals_test.cc, cpp/src/arrow/flight/flight_test.cc, cpp/src/arrow/flight/meson.build, cpp/src/arrow/flight/server.cc, cpp/src/arrow/flight/server.h, cpp/src/arrow/flight/server_tracing_middleware.cc, cpp/src/arrow/flight/transport/grpc/grpc_server.cc, cpp/src/arrow/flight/transport/grpc/grpc_server_internal.cc, cpp/src/arrow/flight/transport/grpc/grpc_server_internal.h

Failure region (last 25 normalized lines):

```
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_io.py:<n>: need sparse file support
skipped [<n>] test_dataset_encryption.py:<n>: parquet encryption is currently enabled
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 3. apache/arrow · regression_strong

- incident `44169b03118d` · 2026-10-21 16:10 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39632318433/job/119333554556
- job: `AMD64 macOS 15-intel C++`
- failed steps: Test
- Gemini likely_cause: The test execution timed out (arrow-s3fs-test and arrow-s3fs-module-test timeout), typically caused by infrastructure slowness or network/resource constraints on the macOS runner.
- fix commit(s):
- https://github.com/apache/arrow/commit/b4a44dee30bb062983d20c091471e0f696cb96e0 (fix run https://github.com/apache/arrow/actions/runs/39744984590)
- touched files: cpp/src/parquet/column_reader_test.cc

Failure region (last 25 normalized lines):

```
no available formula with the name "llvm@<n>". did you mean llvm, llvm@<n>, llvm@<n>, llvm@<n>, llvm@<n>, llvm@<n>, llvm@<n>, llvm@<n>, llvm@<n> or llvm@<n>?
running arrow-s<n>fs-module-test, redirecting output into arrow-s<n>fs-module-test.txt
start <n>: arrow-s<n>fs-module-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
test #<n>: arrow-s<n>fs-module-test .......................***timeout <n>.<n> sec
running arrow-s<n>fs-module-test, redirecting output into arrow-s<n>fs-module-test.txt
<n>% tests passed, <n> tests failed out of <n>
errors while running ctest
label time summary:
arrow-compute-tests = <n>.<n> sec*proc (<n> tests)
arrow-tests = <n>.<n> sec*proc (<n> tests)
arrow_acero = <n>.<n> sec*proc (<n> tests)
arrow_dataset = <n>.<n> sec*proc (<n> tests)
arrow_flight = <n>.<n> sec*proc (<n> tests)
arrow_substrait = <n>.<n> sec*proc (<n> test)
filesystem = <n>.<n> sec*proc (<n> tests)
gandiva-tests = <n>.<n> sec*proc (<n> tests)
parquet-tests = <n>.<n> sec*proc (<n> tests)
unittest = <n>.<n> sec*proc (<n> tests)
total test time (real) = <n>.<n> sec
the following tests failed:
<n> - arrow-s<n>fs-test (timeout) arrow-tests filesystem unittest
<n> - arrow-s<n>fs-module-test (timeout) arrow-tests filesystem unittest
process completed with exit code <n>.
```

**verdict: ___**

## 4. apache/arrow · regression_strong

- incident `dfdcf1c90820` · 2026-10-22 05:01 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39720541198/job/119648773875
- job: `report-extra-cpp / report-ci`
- failed steps: Setup Archery, Send chat message
- Gemini likely_cause: The build failed because a system dependency like libgit2 development headers was missing or not found in the CI runner environment.
- fix commit(s):
- https://github.com/apache/arrow/commit/e53d3f202b8e9bdc3e2b6e59df71f09009233888 (fix run https://github.com/apache/arrow/actions/runs/39898577412)
- touched files: .asf.yaml, cpp/cmake_modules/SetupCxxFlags.cmake, cpp/src/arrow/util/value_parsing.h, cpp/src/arrow/util/value_parsing_test.cc

Failure region (last 25 normalized lines):

```
copying blame.h -> decl
copying attr.h -> decl
running build_ext
generating cffi module 'pygit<n>._libgit<n>.c'
creating temp.linux-x<n>_<n>-cpython-<n>
building 'pygit<n>._pygit<n>' extension
gcc -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer -fno-strict-overflow -wsign-compare -dndebug -g -o<n> -wall -fpic include python<n>.<n> -c blob.c -o blob.o
blob.c:<n>:<n>: fatal error: git<n>.h: no such file or directory
<n> | #include <git<n>.h>
| ^~~~~~~~
compilation terminated.
command '['gcc', '-fno-omit-frame-pointer', '-mno-omit-leaf-frame-pointer', '-fno-strict-overflow', '-wsign-compare', '-dndebug', '-g', '-o<n>', '-wall', '-fpic', 'include', 'python<n>.<n>', '-c', 'blob.c', '-o', 'blob.o
[end of output]
note: this error originates from a subprocess, and is likely not a problem with pip.
failed building wheel for pygit<n>
[notice] a new release of pip is available: <n>.<n>.<n> -> <n>.<n>.<n>
[notice] to update, run: pip install --upgrade pip
failed-wheel-build-for-install
× failed to build installable wheels for some pyproject.toml based projects
╰─> pygit<n>
successfully built archery
failed to build pygit<n>
process completed with exit code <n>.
_temp/<uuid>.sh: line <n>: archery: command not found
process completed with exit code <n>.
```

**verdict: ___**

## 5. apache/arrow · regression_strong

- incident `c072d24f9d58` · 2026-10-22 06:46 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39734440063/job/119681805661
- job: `report-extra-cpp / report-ci`
- failed steps: Setup Archery, Send chat message
- Gemini likely_cause: The build failed because a system dependency like libgit2 development headers was missing or not found in the CI runner environment.
- fix commit(s):
- https://github.com/apache/arrow/commit/e53d3f202b8e9bdc3e2b6e59df71f09009233888 (fix run https://github.com/apache/arrow/actions/runs/39912008131)
- touched files: .asf.yaml, cpp/cmake_modules/SetupCxxFlags.cmake, cpp/src/arrow/util/value_parsing.h, cpp/src/arrow/util/value_parsing_test.cc

Failure region (last 25 normalized lines):

```
copying blame.h -> decl
copying attr.h -> decl
running build_ext
generating cffi module 'pygit<n>._libgit<n>.c'
creating temp.linux-x<n>_<n>-cpython-<n>
building 'pygit<n>._pygit<n>' extension
gcc -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer -fno-strict-overflow -wsign-compare -dndebug -g -o<n> -wall -fpic include python<n>.<n> -c blob.c -o blob.o
blob.c:<n>:<n>: fatal error: git<n>.h: no such file or directory
<n> | #include <git<n>.h>
| ^~~~~~~~
compilation terminated.
command '['gcc', '-fno-omit-frame-pointer', '-mno-omit-leaf-frame-pointer', '-fno-strict-overflow', '-wsign-compare', '-dndebug', '-g', '-o<n>', '-wall', '-fpic', 'include', 'python<n>.<n>', '-c', 'blob.c', '-o', 'blob.o
[end of output]
note: this error originates from a subprocess, and is likely not a problem with pip.
failed building wheel for pygit<n>
[notice] a new release of pip is available: <n>.<n>.<n> -> <n>.<n>.<n>
[notice] to update, run: pip install --upgrade pip
failed-wheel-build-for-install
× failed to build installable wheels for some pyproject.toml based projects
╰─> pygit<n>
successfully built archery
failed to build pygit<n>
process completed with exit code <n>.
_temp/<uuid>.sh: line <n>: archery: command not found
process completed with exit code <n>.
```

**verdict: ___**

## 6. apache/arrow · regression_strong

- incident `fd3b4690bf99` · 2026-10-22 14:02 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39792316721/job/119871182282
- job: `upload`
- failed steps: Download Artifacts
- Gemini likely_cause: The job failed to download artifacts because the expected directories or files were missing or not found in the workspace/git repository.
- fix commit(s):
- https://github.com/apache/arrow/commit/2c800e6bbb8735e868b3b97f041de45095bfdbc5 (fix run https://github.com/apache/arrow/actions/runs/40100715692)
- touched files: .asf.yaml, .github/workflows/package_linux.yml, ci/scripts/r_docker_configure.sh, cpp/cmake_modules/SetupCxxFlags.cmake, cpp/src/arrow/util/value_parsing.h, cpp/src/arrow/util/value_parsing_test.cc, cpp/src/gandiva/engine.cc, cpp/src/gandiva/engine.h, cpp/src/gandiva/filter.cc, cpp/src/gandiva/llvm_generator.cc

Failure region (last 25 normalized lines):

```
-------------------------------------------------------------------------------
[pending] r-binary-packages uploaded <n> / <n>
└ https:/runs/<hex>job/<hex>
└ https:/runs/<hex>job/<hex>
└ https:/runs/<hex>job/<hex>
└ https:/runs/<hex>job/<hex>
└ https:/runs/<hex>job/<hex>
└ https:/runs/<hex>job/<hex>
└ https:/runs/<hex>job/<hex>
└ https:/runs/<hex>job/<hex>***
r-libarrow-windows-x<n>_<n>-<n>.<n>.<n>.<hex>.zip [pending]
r-libarrow-linux-x<n>_<n>-<n>.<n>.<n>.<hex>.zip [pending]
r-libarrow-linux-arm<n>-<n>.<n>.<n>.<hex>.zip [pending]
r-libarrow-darwin-arm<n>-<n>.<n>.<n>.<hex>.zip [pending]
r-libarrow-darwin-x<n>_<n>-<n>.<n>.<n>.<hex>.zip [pending]
r-pkg__bin__windows__contrib__<n>.<n>__arrow_<n>.<n>.<n>.<hex>.zip [pending]
r-pkg__bin__windows__contrib__<n>.<n>__arrow_<n>.<n>.<n>.<hex>.zip [pending]
r-pkg__bin__macosx__big-sur-x<n>_<n>__contrib__<n>.<n>__arrow_<n>.<n>.<n>.<hex>.tgz [pending]
r-pkg__bin__macosx__big-sur-x<n>_<n>__contrib__<n>.<n>__arrow_<n>.<n>.<n>.<hex>.tgz [pending]
r-pkg__bin__macosx__big-sur-arm<n>__contrib__<n>.<n>__arrow_<n>.<n>.<n>.<hex>.tgz [pending]
r-pkg__bin__macosx__sonoma-arm<n>__contrib__<n>.<n>__arrow_<n>.<n>.<n>.<hex>.tgz [pending]
r-pkg__src__contrib__arrow_<n>.<n>.<n>.<hex>.gz [pending]
ls: cannot access 'binaries/*/*/': no such file or directory
no files found. stopping upload.
process completed with exit code <n>.
```

**verdict: ___**

## 7. apache/arrow · regression_strong

- incident `cfed1562be88` · 2026-10-22 14:24 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39795105178/job/119880348652
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: Homebrew dependency resolution failed because formula 'llvm@<n>' was not available or removed during package installation.
- fix commit(s):
- https://github.com/apache/arrow/commit/e53d3f202b8e9bdc3e2b6e59df71f09009233888 (fix run https://github.com/apache/arrow/actions/runs/39892983056)
- touched files: .asf.yaml, cpp/cmake_modules/SetupCxxFlags.cmake

Failure region (last 25 normalized lines):

```
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_io.py:<n>: need sparse file support
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
skipped [<n>] test_dlpack.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 8. apache/arrow · regression_strong

- incident `5ca36977956d` · 2026-10-22 14:26 UTC · 2 job(s) · https://github.com/apache/arrow/actions/runs/39795590458/job/119882012574
- job: `AMD64 Ubuntu 24.04 C++ ASAN UBSAN`
- failed steps: Execute Docker Build
- Gemini likely_cause: Docker build failed due to infrastructure or network issue during container image creation or package download.
- fix commit(s):
- https://github.com/apache/arrow/commit/9de25d933b9c9c503f1098a4456f2772b8a60ed4 (fix run https://github.com/apache/arrow/actions/runs/39859473765)
- touched files: cpp/cmake_modules/ThirdpartyToolchain.cmake, cpp/cmake_modules/google-cloud-cpp-openssl4-compatibility.patch, cpp/thirdparty/versions.txt

Failure region (last 25 normalized lines):

```
pandas: latest
python: <n>.<n>
python_abi_tag: cp<n>
python_image_tag: <n>.<n>
python_wheel_windows_image_revision: <n>-<n>-<n>
python_wheel_windows_test_image_revision: <n>-<n>-<n>
r: <n>.<n>
repo: arrow-dev
r_custom_ccache: false
r_image: ubuntu-release
r_org: rhub
r_prune_deps: false
r_tag: latest
spark: master
tz: utc
ubuntu: <n>.<n>
ulimit_core: -<n>
vcpkg: <hex>
archery was called with:
export arch=amd<n>
export clang_tools=<n>
export docker_volume_prefix=.docker/
export llvm=<n>
export ubuntu=<n>.<n>
process completed with exit code <n>.
```

**verdict: ___**

## 9. apache/arrow · regression_strong

- incident `17a881e851d2` · 2026-10-23 03:31 UTC · 5 job(s) · https://github.com/apache/arrow/actions/runs/39892983276/job/120223890380
- job: `debian-forky-amd64`
- failed steps: Verify Reproducibility
- Gemini likely_cause: A BrokenPipeError occurred during the reproducibility test execution within the testbed/virtual server communication.
- fix commit(s):
- https://github.com/apache/arrow/commit/2c800e6bbb8735e868b3b97f041de45095bfdbc5 (fix run https://github.com/apache/arrow/actions/runs/39968408924)
- touched files: .github/workflows/package_linux.yml, ci/scripts/r_docker_configure.sh, cpp/src/gandiva/engine.cc, cpp/src/gandiva/engine.h, cpp/src/gandiva/filter.cc, cpp/src/gandiva/llvm_generator.cc, cpp/src/gandiva/llvm_generator.h, cpp/src/gandiva/projector.cc, cpp/src/gandiva/tests/CMakeLists.txt, cpp/src/gandiva/tests/cache_race_test.cc

Failure region (last 25 normalized lines):

```
^^^^^^^^^^^^^^^^^^^^^^^^
file "contextlib.py", line <n>, in __exit__
self.gen.throw(value)
~~~~~~~~~~~~~~^^^^^^^
file "__init__.py", line <n>, in start_testbed
testbed.stop()
~~~~~~~~~~~~^^
file "adt_testbed.py", line <n>, in stop
self.close()
~~~~~~~~~~^^
file "adt_testbed.py", line <n>, in close
self.command('close')
~~~~~~~~~~~~^^^^^^^^^
file "adt_testbed.py", line <n>, in command
self.send(' '.join(al))
~~~~~~~~~^^^^^^^^^^^^^^
file "adt_testbed.py", line <n>, in send
self.bomb('cannot send to testbed: %s' % traceback.
~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
format_exception_only(type, value))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
file "__init__.py", line <n>, in bomb
raise _type(m)
reprotest.lib.adtlog.testbedfailure: cannot send to testbed: ['brokenpipeerror: [errno <n>] broken n']
process completed with exit code <n>.
```

**verdict: ___**

## 10. apache/arrow · regression_strong

- incident `50c2fa3834ae` · 2026-10-23 13:54 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39964912350/job/120452142645
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: Homebrew dependency resolution failure due to a missing formula 'llvm@...' on the macOS CI runner environment.
- fix commit(s):
- https://github.com/apache/arrow/commit/d228ba5a9def26e67e12b2e475be0b00edb77aea (fix run https://github.com/apache/arrow/actions/runs/40255173485)
- touched files: .github/workflows/package_linux.yml, ci/scripts/r_docker_configure.sh, cpp/src/arrow/util/value_parsing.h, cpp/src/arrow/util/value_parsing_test.cc, cpp/src/gandiva/to_date_holder_test.cc

Failure region (last 25 normalized lines):

```
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_io.py:<n>: need sparse file support
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 11. apache/arrow · regression_strong

- incident `386bcd44d57e` · 2026-10-23 13:55 UTC · 5 job(s) · https://github.com/apache/arrow/actions/runs/39964912865/job/120452967867
- job: `ubuntu-noble-amd64`
- failed steps: Verify Reproducibility
- Gemini likely_cause: The test failed due to a BrokenPipeError communicating with the testbed during reproducibility verification, indicating an infrastructure or environment communication issue.
- fix commit(s):
- https://github.com/apache/arrow/commit/2c800e6bbb8735e868b3b97f041de45095bfdbc5 (fix run https://github.com/apache/arrow/actions/runs/39968408924)
- touched files: .github/workflows/package_linux.yml, ci/scripts/r_docker_configure.sh

Failure region (last 25 normalized lines):

```
^^^^^^^^^^^^^^^^^^^^^^^^
file "contextlib.py", line <n>, in __exit__
self.gen.throw(value)
~~~~~~~~~~~~~~^^^^^^^
file "__init__.py", line <n>, in start_testbed
testbed.stop()
~~~~~~~~~~~~^^
file "adt_testbed.py", line <n>, in stop
self.close()
~~~~~~~~~~^^
file "adt_testbed.py", line <n>, in close
self.command('close')
~~~~~~~~~~~~^^^^^^^^^
file "adt_testbed.py", line <n>, in command
self.send(' '.join(al))
~~~~~~~~~^^^^^^^^^^^^^^
file "adt_testbed.py", line <n>, in send
self.bomb('cannot send to testbed: %s' % traceback.
~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
format_exception_only(type, value))
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
file "__init__.py", line <n>, in bomb
raise _type(m)
reprotest.lib.adtlog.testbedfailure: cannot send to testbed: ['brokenpipeerror: [errno <n>] broken n']
process completed with exit code <n>.
```

**verdict: ___**

## 12. mpv-player/mpv · regression_strong

- incident `e2f2fd869122` · 2026-10-25 21:30 UTC · 1 job(s) · https://github.com/mpv-player/mpv/actions/runs/40235824216/job/121297064500
- job: `mingw (i686, wine32)`
- failed steps: Build libraries
- Gemini likely_cause: Wine failed to run the cross-compiled test binary due to a socket/polling error in the CI environment.
- fix commit(s):
- https://github.com/mpv-player/mpv/commit/723b32b6cb1d6e88aca155ee2a2679c52bf91908 (fix run https://github.com/mpv-player/mpv/actions/runs/41196156029)
- touched files: .github/workflows/build.yml, DOCS/interface-changes/use-tone-constants.txt, DOCS/man/options.rst, audio/out/ao_alsa.c, ci/build-freebsd.sh, ci/build-linux-old.sh, ci/build-mingw64-full.sh, ci/build-openbsd.sh, common/msg.c, demux/demux.c

Failure region (last 25 normalized lines):

```
this program is free software; you may redistribute it under the terms of
the gnu general public license version <n> or (at your option) a later version.
this program has absolutely no warranty.
-----------
stderr:
collect<n> version <n>-posix
i<n>-w<n>-mingw<n>-ld -plugin liblto_plugin.so -plugin-opt=lto-wrapper -plugin-opt=-fresolution=cccqejym.res -plugin-opt=-pass-through=-lmingw<n> -plugin-opt=-pass-through=-lgcc -plugin-opt=-pass-through=-lgcc_eh -plugin
-----------
sanity testing c compiler: ccache i<n>-w<n>-mingw<n>-gcc-posix
is cross compiler: true.
sanity check compiler command line: ccache i<n>-w<n>-mingw<n>-gcc-posix sanitycheckc.c -o sanitycheckc_cross.exe -o<n> -pipe -wall -u_fortify_source -d_fortify_source=<n> -d_file_offset_bits=<n> -fstack-protector-strong
sanity check compile stdout:
-----
sanity check compile stderr:
-----
running test binary command: wine sanitycheckc_cross.exe
-----------
sanity check: `wine sanitycheckc_cross.exe` -> <n>
stderr:
sock_init: error in sock_check_pollhup()
wineserver: socket: function not implemented
-----------
meson.build:<n>:<n>: error: executables created by c compiler ccache i<n>-w<n>-mingw<n>-gcc-posix are not runnable.
##[endgroup]
process completed with exit code <n>.
```

**verdict: ___**

## 13. apache/arrow · regression_strong

- incident `5544b0ead1c6` · 2026-10-26 11:25 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/40314945198/job/121545073217
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: Homebrew dependency resolution failure due to a missing formula 'llvm@<n>' during setup.
- fix commit(s):
- https://github.com/apache/arrow/commit/a72e35be411bbca7381828973559ef986878474f (fix run https://github.com/apache/arrow/actions/runs/40371174104)
- touched files: .pre-commit-config.yaml, docs/source/developers/python/development.rst, python/pyarrow-stubs/pyarrow/_ipc.pyi, python/pyarrow-stubs/pyarrow/array.pyi, python/pyarrow-stubs/pyarrow/table.pyi, python/pyarrow-stubs/pyarrow/types.pyi, python/pyarrow-stubs/tests/_check.py, python/pyarrow-stubs/tests/test_array.py, python/pyarrow-stubs/tests/test_table.py, python/pyarrow-stubs/tests/test_types.py

Failure region (last 25 normalized lines):

```
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_io.py:<n>: need sparse file support
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_dataset_encryption.py:<n>: parquet encryption is currently enabled
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 14. mpv-player/mpv · regression_strong

- incident `6c604e477f09` · 2026-10-26 14:23 UTC · 2 job(s) · https://github.com/mpv-player/mpv/actions/runs/40339198709/job/121628909669
- job: `mingw (i686, wine32)`
- failed steps: Build libraries
- Gemini likely_cause: The wine environment failed to execute the cross-compiled test binary due to a socket/polling function not implemented issue in the CI runner's wine setup.
- fix commit(s):
- https://github.com/mpv-player/mpv/commit/1cc1b8cf1161cc9e95f17824ac0eea2d0b8e037d (fix run https://github.com/mpv-player/mpv/actions/runs/40375982347)
- touched files: .github/workflows/build.yml

Failure region (last 25 normalized lines):

```
this program is free software; you may redistribute it under the terms of
the gnu general public license version <n> or (at your option) a later version.
this program has absolutely no warranty.
-----------
stderr:
collect<n> version <n>-posix
i<n>-w<n>-mingw<n>-ld -plugin liblto_plugin.so -plugin-opt=lto-wrapper -plugin-opt=-fresolution=cc<n>h<n>qaa.res -plugin-opt=-pass-through=-lmingw<n> -plugin-opt=-pass-through=-lgcc -plugin-opt=-pass-through=-lgcc_eh -pl
-----------
sanity testing c compiler: ccache i<n>-w<n>-mingw<n>-gcc-posix
is cross compiler: true.
sanity check compiler command line: ccache i<n>-w<n>-mingw<n>-gcc-posix sanitycheckc.c -o sanitycheckc_cross.exe -o<n> -pipe -wall -u_fortify_source -d_fortify_source=<n> -d_file_offset_bits=<n> -fstack-protector-strong
sanity check compile stdout:
-----
sanity check compile stderr:
-----
running test binary command: wine sanitycheckc_cross.exe
-----------
sanity check: `wine sanitycheckc_cross.exe` -> <n>
stderr:
sock_init: error in sock_check_pollhup()
wineserver: socket: function not implemented
-----------
meson.build:<n>:<n>: error: executables created by c compiler ccache i<n>-w<n>-mingw<n>-gcc-posix are not runnable.
##[endgroup]
process completed with exit code <n>.
```

**verdict: ___**

## 15. apache/arrow · regression_strong

- incident `c10dfbbc2121` · 2026-10-26 15:32 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/40350172433/job/121667750101
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: The CI job failed during the test phase because a required dependency tool ('azurite-blob') was missing or could not be found in the environment's PATH.
- fix commit(s):
- https://github.com/apache/arrow/commit/a72e35be411bbca7381828973559ef986878474f (fix run https://github.com/apache/arrow/actions/runs/40371174104)
- touched files: .pre-commit-config.yaml, docs/source/developers/python/development.rst, python/pyarrow-stubs/pyarrow/_ipc.pyi, python/pyarrow-stubs/pyarrow/array.pyi, python/pyarrow-stubs/pyarrow/table.pyi, python/pyarrow-stubs/pyarrow/types.pyi, python/pyarrow-stubs/tests/test_array.py, python/pyarrow-stubs/tests/test_table.py, python/pyarrow-stubs/tests/test_types.py, python/pyarrow/tests/test_types.py

Failure region (last 25 normalized lines):

```
skipped [<n>] test_fs.py:<n>: could not import 'fsspec': no module named 'fsspec'
skipped [<n>] test_fs.py:<n>: could not import 's<n>fs': no module named 's<n>fs'
skipped [<n>] test_fs.py:<n>: command ['azurite-blob', '--location', local('popen-gw<n>'), '--blobport', '<n>', '--skipapiversioncheck'] failed to execute: [errno <n>] no such file or directory: 'azurite-blob'
skipped [<n>] test_fs.py:<n>: cannot locate libhdfs
skipped [<n>] test_fs.py:<n>: could not import 'fsspec': no module named 'fsspec'
skipped [<n>] test_fs.py:<n>: could not import 's<n>fs': no module named 's<n>fs'
skipped [<n>] test_fs.py:<n>: command ['azurite-blob', '--location', local('popen-gw<n>'), '--blobport', '<n>', '--skipapiversioncheck'] failed to execute: [errno <n>] no such file or directory: 'azurite-blob'
skipped [<n>] test_fs.py:<n>: cannot locate libhdfs
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
skipped [<n>] test_dlpack.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 16. apache/arrow · regression_weak

- incident `3b908810fdc7` · 2026-10-21 09:32 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39577677290/job/119147162369
- job: `ARM64 macOS 14 C++`
- failed steps: Test
- Gemini likely_cause: The test timed out on the ARM64 macOS runner, which is characteristic of an infrastructure performance issue or job timeout.
- fix commit(s):
- https://github.com/apache/arrow/commit/3d77c491034c2229b8d6a6d3e190983a733616e0 (fix run https://github.com/apache/arrow/actions/runs/39632318433)
- touched files: cpp/src/arrow/flight/CMakeLists.txt, cpp/src/arrow/flight/flight_internals_test.cc, cpp/src/arrow/flight/flight_test.cc, cpp/src/arrow/flight/meson.build, cpp/src/arrow/flight/server.cc, cpp/src/arrow/flight/server.h, cpp/src/arrow/flight/server_tracing_middleware.cc, cpp/src/arrow/flight/transport/grpc/grpc_server.cc, cpp/src/arrow/flight/transport/grpc/grpc_server_internal.cc, cpp/src/arrow/flight/transport/grpc/grpc_server_internal.h

Failure region (last 25 normalized lines):

```
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
<n>% tests passed, <n> tests failed out of <n>
label time summary:
arrow-compute-tests = <n>.<n> sec*proc (<n> tests)
arrow-tests = <n>.<n> sec*proc (<n> tests)
arrow_acero = <n>.<n> sec*proc (<n> tests)
arrow_dataset = <n>.<n> sec*proc (<n> tests)
arrow_flight = <n>.<n> sec*proc (<n> tests)
arrow_substrait = <n>.<n> sec*proc (<n> test)
filesystem = <n>.<n> sec*proc (<n> tests)
gandiva-tests = <n>.<n> sec*proc (<n> tests)
parquet-tests = <n>.<n> sec*proc (<n> tests)
unittest = <n>.<n> sec*proc (<n> tests)
total test time (real) = <n>.<n> sec
the following tests failed:
<n> - arrow-s<n>fs-test (timeout) arrow-tests filesystem unittest
errors while running ctest
process completed with exit code <n>.
```

**verdict: ___**

## 17. apache/arrow · regression_weak

- incident `78578cc1e69f` · 2026-10-21 10:37 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39585707161/job/119173940721
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: An infrastructure issue occurred during dependency installation on macOS when Homebrew failed to locate a formula (llvm@<n>).
- fix commit(s):
- https://github.com/apache/arrow/commit/54532f4d28a20bdb634ced9cc4518d31891a7b84 (fix run https://github.com/apache/arrow/actions/runs/39748745196)
- touched files: cpp/src/arrow/compute/kernels/codegen_internal.cc, cpp/src/arrow/compute/kernels/codegen_internal.h, cpp/src/arrow/compute/kernels/scalar_compare.cc, cpp/src/arrow/compute/kernels/scalar_nested.cc, cpp/src/arrow/compute/kernels/scalar_nested_test.cc

Failure region (last 25 normalized lines):

```
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_io.py:<n>: need sparse file support
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 18. apache/arrow · regression_weak

- incident `46a85edfc0f8` · 2026-10-21 17:07 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39640964584/job/119364044139
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: An infrastructure issue occurred during dependency installation on macOS when Homebrew failed to locate a formula (llvm@<n>).
- fix commit(s):
- https://github.com/apache/arrow/commit/84833d29c903899648838609ac037760d95dc798 (fix run https://github.com/apache/arrow/actions/runs/39756099533)
- touched files: python/CMakeLists.txt, r/configure, r/configure.win

Failure region (last 25 normalized lines):

```
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_io.py:<n>: need sparse file support
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 19. apache/arrow · regression_weak

- incident `a64aec41f027` · 2026-10-22 14:26 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39795590436/job/119882014020
- job: `AMD64 Ubuntu 24.04 R 4.6 Force-Tests true`
- failed steps: Execute Docker Build, Dump install logs, Dump test logs
- Gemini likely_cause: Docker container build or execution failed, resulting in missing installation and test log files during the CI job.
- fix commit(s):
- https://github.com/apache/arrow/commit/9de25d933b9c9c503f1098a4456f2772b8a60ed4 (fix run https://github.com/apache/arrow/actions/runs/39859473608)
- touched files: cpp/cmake_modules/ThirdpartyToolchain.cmake, cpp/cmake_modules/google-cloud-cpp-openssl4-compatibility.patch, cpp/thirdparty/versions.txt

Failure region (last 25 normalized lines):

```
python_abi_tag: cp<n>
python_image_tag: <n>.<n>
python_wheel_windows_image_revision: <n>-<n>-<n>
python_wheel_windows_test_image_revision: <n>-<n>-<n>
r: <n>.<n>
repo: arrow-dev
r_custom_ccache: false
r_image: ubuntu-release
r_org: rhub
r_prune_deps: false
r_tag: latest
spark: master
tz: utc
ubuntu: <n>.<n>
ulimit_core: -<n>
vcpkg: <hex>
archery was called with:
export docker_volume_prefix=.docker/
export r=<n>.<n>
export ubuntu=<n>.<n>
process completed with exit code <n>.
cat: <n>install.out: no such file or directory
process completed with exit code <n>.
cat: 'testthat.rout*': no such file or directory
process completed with exit code <n>.
```

**verdict: ___**

## 20. apache/arrow · regression_weak

- incident `1db22e6cb7ce` · 2026-10-22 14:26 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39795590458/job/119882012165
- job: `ARM64 macOS 14 C++`
- failed steps: Build
- Gemini likely_cause: The build failed because CMake's FetchContent failed to find a suitable version of curl while building google-cloud-cpp from source on the runner environment.
- fix commit(s):
- https://github.com/apache/arrow/commit/9de25d933b9c9c503f1098a4456f2772b8a60ed4 (fix run https://github.com/apache/arrow/actions/runs/39859473765)
- touched files: cpp/cmake_modules/ThirdpartyToolchain.cmake, cpp/cmake_modules/google-cloud-cpp-openssl4-compatibility.patch, cpp/thirdparty/versions.txt

Failure region (last 25 normalized lines):

```
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_wextra
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_wextra - success
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_wconversion
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_wconversion - success
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_wno_sign_conversion
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_wno_sign_conversion - success
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_werror
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_werror - success
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_clang_abi_compat_<n>
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_clang_abi_compat_<n> - failed
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_pedantic
-- google-cloud-cpp: performing test google_cloud_cpp_compiler_supports_pedantic - success
-- google-cloud-cpp: found openssl: openssl@libcrypto.dylib (found version "<n>.<n>.<n>")
cmake error at findpackagehandlestandardargs.cmake:<n> (message):
could not find curl: found unsuitable version "<n>.<n>.<n>", but required is at
least "<n>.<n>.<n>" (found
libcurl.tbd,
)
call stack (most recent call first):
findpackagehandlestandardargs.cmake:<n> (_fphsa_failure_message)
findcurl.cmake:<n> (find_package_handle_standard_args)
google_cloud_cpp_rest_internal.cmake:<n> (find_package)
cmakelists.txt:<n> (include)
-- configuring incomplete, errors occurred!
process completed with exit code <n>.
```

**verdict: ___**

## 21. apache/arrow · regression_weak

- incident `c32afde12a2c` · 2026-10-22 14:26 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39795105387/job/119882152782
- job: `almalinux-10-arm64`
- failed steps: Test
- Gemini likely_cause: The Docker daemon is not running or unavailable on the CI runner, causing docker commands to fail.
- fix commit(s):
- https://github.com/apache/arrow/commit/14132604b3949ba1c25cc79fff2e1782b9efc413 (fix run https://github.com/apache/arrow/actions/runs/39888979190)
- touched files: .asf.yaml

Failure region (last 25 normalized lines):

```
binary-task.rb:<n>:in `verify'
binary-task.rb:<n>:in `block (<n> levels) in define_yum_test_task'
binary-task.rb:<n>:in `each'
binary-task.rb:<n>:in `block (<n> levels) in define_yum_test_task'
task.rb:<n>:in `block in execute'
task.rb:<n>:in `each'
task.rb:<n>:in `execute'
task.rb:<n>:in `block in invoke_with_call_chain'
task.rb:<n>:in `synchronize'
task.rb:<n>:in `invoke_with_call_chain'
task.rb:<n>:in `invoke'
application.rb:<n>:in `invoke_task'
application.rb:<n>:in `block (<n> levels) in top_level'
application.rb:<n>:in `each'
application.rb:<n>:in `block in top_level'
application.rb:<n>:in `run_with_threads'
application.rb:<n>:in `top_level'
application.rb:<n>:in `block in run'
application.rb:<n>:in `standard_exception_handling'
application.rb:<n>:in `run'
rake:<n>:in `<top (required)>'
rake:<n>:in `load'
rake:<n>:in `<main>'
tasks: top => yum:test
process completed with exit code <n>.
```

**verdict: ___**

## 22. apache/arrow · regression_weak

- incident `265c208bce02` · 2026-10-23 13:54 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/39964912841/job/120452144618
- job: `ARM64 macOS 14 C++`
- failed steps: Test
- Gemini likely_cause: The test timed out on the ARM64 macOS runner, which is characteristic of an infrastructure performance issue or job timeout.
- fix commit(s):
- https://github.com/apache/arrow/commit/d228ba5a9def26e67e12b2e475be0b00edb77aea (fix run https://github.com/apache/arrow/actions/runs/40255173593)
- touched files: .github/workflows/package_linux.yml, ci/scripts/r_docker_configure.sh, cpp/src/arrow/util/value_parsing.h, cpp/src/arrow/util/value_parsing_test.cc, cpp/src/gandiva/to_date_holder_test.cc

Failure region (last 25 normalized lines):

```
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
<n>% tests passed, <n> tests failed out of <n>
label time summary:
arrow-compute-tests = <n>.<n> sec*proc (<n> tests)
arrow-tests = <n>.<n> sec*proc (<n> tests)
arrow_acero = <n>.<n> sec*proc (<n> tests)
arrow_dataset = <n>.<n> sec*proc (<n> tests)
arrow_flight = <n>.<n> sec*proc (<n> tests)
arrow_substrait = <n>.<n> sec*proc (<n> test)
filesystem = <n>.<n> sec*proc (<n> tests)
gandiva-tests = <n>.<n> sec*proc (<n> tests)
parquet-tests = <n>.<n> sec*proc (<n> tests)
unittest = <n>.<n> sec*proc (<n> tests)
total test time (real) = <n>.<n> sec
the following tests failed:
<n> - arrow-s<n>fs-test (timeout) arrow-tests filesystem unittest
errors while running ctest
process completed with exit code <n>.
```

**verdict: ___**

## 23. apache/arrow · regression_weak

- incident `aa91d3011449` · 2026-10-24 06:27 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/40070255384/job/120801958694
- job: `ARM64 macOS 14 C++`
- failed steps: Test
- Gemini likely_cause: The test timed out on the ARM64 macOS runner, which is characteristic of an infrastructure or resource constraint issue on the CI runner.
- fix commit(s):
- https://github.com/apache/arrow/commit/4580b180b1447697adc8ecf72a8f3fde07705f46 (fix run https://github.com/apache/arrow/actions/runs/41506482527)
- touched files: .env, .github/actions/odbc-windows/action.yml, .github/workflows/cpp.yml, .github/workflows/cpp_extra.yml, .github/workflows/cpp_windows.yml, .github/workflows/cuda_extra.yml, .github/workflows/package_linux.yml, .github/workflows/package_odbc.yml, .github/workflows/python.yml, .github/workflows/r_extra.yml

Failure region (last 25 normalized lines):

```
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
start <n>: arrow-s<n>fs-test
test #<n>: arrow-s<n>fs-test ..............................***timeout <n>.<n> sec
running arrow-s<n>fs-test, redirecting output into arrow-s<n>fs-test.txt
<n>% tests passed, <n> tests failed out of <n>
label time summary:
arrow-compute-tests = <n>.<n> sec*proc (<n> tests)
arrow-tests = <n>.<n> sec*proc (<n> tests)
arrow_acero = <n>.<n> sec*proc (<n> tests)
arrow_dataset = <n>.<n> sec*proc (<n> tests)
arrow_flight = <n>.<n> sec*proc (<n> tests)
arrow_substrait = <n>.<n> sec*proc (<n> test)
filesystem = <n>.<n> sec*proc (<n> tests)
gandiva-tests = <n>.<n> sec*proc (<n> tests)
parquet-tests = <n>.<n> sec*proc (<n> tests)
unittest = <n>.<n> sec*proc (<n> tests)
total test time (real) = <n>.<n> sec
the following tests failed:
errors while running ctest
<n> - arrow-s<n>fs-test (timeout) arrow-tests filesystem unittest
process completed with exit code <n>.
```

**verdict: ___**

## 24. apache/arrow · regression_weak

- incident `7b3182e524f4` · 2026-10-24 23:30 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/40143026804/job/121018583334
- job: `ARM64 Windows 11 MSVC / windows`
- failed steps: Build
- Gemini likely_cause: The build failed due to a network connection timeout/error while downloading external dependencies (Apache ORC) via CMake FetchContent.
- fix commit(s):
- https://github.com/apache/arrow/commit/1bc6ba19c2d8ef7e3c00e9fdeadf7f85398955c8 (fix run https://github.com/apache/arrow/actions/runs/40177558040)
- touched files: cpp/src/arrow/compute/row/row_encoder_internal.cc, cpp/src/arrow/compute/row/row_encoder_internal.h, cpp/src/arrow/compute/row/row_encoder_internal_test.cc

Failure region (last 25 normalized lines):

```
apache orc:
apache orc:
apache orc: --- log end ---
apache orc:
apache orc:
apache orc:
apache orc:
apache orc: failed: [code=<n>] orc-populate-download orc-populate-download
apache orc: cmd.exe c "cd d _deps && "program cmake.exe" -dcmake_message_log_level=verbose -p download-orc-populate.cmake && "program cmake.exe" -dcmake_message_log_level=verbose -p verify-orc-populate.cmake && "program 
apache orc: ninja: build stopped: subcommand failed.
apache orc:
cmake error at program fetchcontent.cmake:<n> (message):
build step for orc failed: <n>
call stack (most recent call first):
program fetchcontent.cmake:<n> (__fetchcontent_populatesubbuild)
program fetchcontent.cmake:<n>:eval:<n> (__fetchcontent_dopopulation)
program fetchcontent.cmake:<n> (cmake_language)
program fetchcontent.cmake:<n> (__fetchcontent_populate)
thirdpartytoolchain.cmake:<n> (fetchcontent_makeavailable)
thirdpartytoolchain.cmake:<n> (build_orc)
thirdpartytoolchain.cmake:<n> (build_dependency)
thirdpartytoolchain.cmake:<n> (resolve_dependency)
cmakelists.txt:<n> (include)
-- configuring incomplete, errors occurred!
process completed with exit code <n>.
```

**verdict: ___**

## 25. apache/arrow · regression_weak

- incident `68c33163a331` · 2026-10-26 11:25 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/40314945300/job/121545073243
- job: `AMD64 Conda Python 3.12 Sphinx Documentation`
- failed steps: Execute Docker Build
- Gemini likely_cause: The Docker build failed during the Sphinx documentation generation job, typically indicating a container environment or resource setup issue.
- fix commit(s):
- https://github.com/apache/arrow/commit/c347f7f2b456756528fe874d2dae724d4a2619ed (fix run https://github.com/apache/arrow/actions/runs/40350172579)
- touched files: docs/source/developers/python/development.rst, python/pyarrow-stubs/pyarrow/_ipc.pyi, python/pyarrow-stubs/tests/_check.py, python/pyproject.toml

Failure region (last 25 normalized lines):

```
numba: latest
numba_cuda: latest
numpy: latest
pandas: latest
python: <n>.<n>
python_abi_tag: cp<n>
python_image_tag: <n>.<n>
python_wheel_windows_image_revision: <n>-<n>-<n>
python_wheel_windows_test_image_revision: <n>-<n>-<n>
r: <n>.<n>
repo: arrow-dev
r_custom_ccache: false
r_image: ubuntu-release
r_org: rhub
r_prune_deps: false
r_tag: latest
spark: master
tz: utc
ubuntu: <n>.<n>
ulimit_core: -<n>
vcpkg: <hex>
archery was called with:
export docker_volume_prefix=.docker/
export python=<n>.<n>
process completed with exit code <n>.
```

**verdict: ___**

## 26. apache/arrow · regression_weak

- incident `852fcb0e3dc4` · 2026-10-26 11:25 UTC · 5 job(s) · https://github.com/apache/arrow/actions/runs/40314945198/job/121545073646
- job: `AMD64 Conda Python 3.12 Sphinx & Numpydoc`
- failed steps: Execute Docker Build
- Gemini likely_cause: The Docker build failed during infrastructure execution or dependency setup within the CI environment.
- fix commit(s):
- https://github.com/apache/arrow/commit/a72e35be411bbca7381828973559ef986878474f (fix run https://github.com/apache/arrow/actions/runs/40371174104)
- https://github.com/apache/arrow/commit/c347f7f2b456756528fe874d2dae724d4a2619ed (fix run https://github.com/apache/arrow/actions/runs/40350172433)
- touched files: .pre-commit-config.yaml, docs/source/developers/python/development.rst, python/pyarrow-stubs/pyarrow/_ipc.pyi, python/pyarrow-stubs/pyarrow/array.pyi, python/pyarrow-stubs/pyarrow/table.pyi, python/pyarrow-stubs/pyarrow/types.pyi, python/pyarrow-stubs/tests/_check.py, python/pyarrow-stubs/tests/test_array.py, python/pyarrow-stubs/tests/test_table.py, python/pyarrow-stubs/tests/test_types.py

Failure region (last 25 normalized lines):

```
pandas: latest
python: <n>.<n>
python_abi_tag: cp<n>
python_image_tag: <n>.<n>
python_wheel_windows_image_revision: <n>-<n>-<n>
python_wheel_windows_test_image_revision: <n>-<n>-<n>
r: <n>.<n>
repo: arrow-dev
r_custom_ccache: false
r_image: ubuntu-release
r_org: rhub
r_prune_deps: false
r_tag: latest
spark: master
tz: utc
ubuntu: <n>.<n>
ulimit_core: -<n>
vcpkg: <hex>
archery was called with:
export docker_volume_prefix=.docker/
export numpy=latest
export pandas=latest
export python=<n>.<n>
export ubuntu=<n>.<n>
process completed with exit code <n>.
```

**verdict: ___**

## 27. apache/arrow · regression_weak

- incident `372ca5292729` · 2026-10-26 15:10 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/40346659122/job/121655269312
- job: `AMD64 Windows MinGW MINGW64 C++`
- failed steps: Test
- Gemini likely_cause: The test job failed due to a test timeout (arrow-flight-test (timeout)), which is characteristic of an infrastructure or resource issue on the CI runner.
- fix commit(s):
- https://github.com/apache/arrow/commit/5f75a12e29d2ccf1c5527db0750c8b5ce6aa9ce1 (fix run https://github.com/apache/arrow/actions/runs/40477406026)
- touched files: cpp/src/parquet/arrow/arrow_reader_writer_test.cc, cpp/src/parquet/arrow/path_internal.cc, cpp/src/parquet/column_writer.cc, docs/source/cpp/security.rst, docs/source/format/Security.rst, docs/source/python/api/compute.rst, python/pyarrow/_compute.pyx, python/pyarrow/_flight.pyx, python/pyarrow/array.pxi, python/pyarrow/compute.py

Failure region (last 25 normalized lines):

```
[----------] global test environment tear-down
[==========] <n> tests from <n> test suites ran. (<n> ms total)
[ passed ] <n> tests.
[ skipped ] <n> tests, listed below:
[ skipped ] grpccudadatatest.testdoget
[ skipped ] grpccudadatatest.testdoput
[ skipped ] grpccudadatatest.testdoexchange
you have <n> disabled tests
<n>% tests passed, <n> tests failed out of <n>
label time summary:
arrow-compute-tests = <n>.<n> sec*proc (<n> tests)
arrow-tests = <n>.<n> sec*proc (<n> tests)
arrow_acero = <n>.<n> sec*proc (<n> tests)
arrow_dataset = <n>.<n> sec*proc (<n> tests)
arrow_flight = <n>.<n> sec*proc (<n> tests)
arrow_flight_sql = <n>.<n> sec*proc (<n> test)
arrow_substrait = <n>.<n> sec*proc (<n> test)
filesystem = <n>.<n> sec*proc (<n> tests)
parquet-tests = <n>.<n> sec*proc (<n> tests)
unittest = <n>.<n> sec*proc (<n> tests)
total test time (real) = <n>.<n> sec
the following tests failed:
<n> - arrow-flight-test (timeout) arrow_flight unittest
process completed with exit code <n>.
```

**verdict: ___**

## 28. apache/arrow · regression_weak

- incident `e75eb2b93a45` · 2026-10-26 15:11 UTC · 1 job(s) · https://github.com/apache/arrow/actions/runs/40346658594/job/121655267970
- job: `AMD64 macOS 15-intel Python 3`
- failed steps: Test
- Gemini likely_cause: Homebrew dependency resolution failure due to a missing or renamed formula ('llvm@<n>') on the macOS runner.
- fix commit(s):
- https://github.com/apache/arrow/commit/4a6ebc06dc2bb967263fdf83449ac104e54cbaba (fix run https://github.com/apache/arrow/actions/runs/40383422501)
- touched files: docs/source/python/api/compute.rst, python/pyarrow/_compute.pyx, python/pyarrow/_flight.pyx, python/pyarrow/array.pxi, python/pyarrow/compute.py, python/pyarrow/orc.py, python/pyarrow/parquet/core.py, python/pyarrow/table.pxi, python/pyarrow/tests/parquet/test_basic.py, python/pyarrow/tests/test_array.py

Failure region (last 25 normalized lines):

```
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_gdb.py:<n>: gdb command unavailable
skipped [<n>] test_io.py:<n>: need sparse file support
skipped [<n>] test_json.py:<n>: test crashes in debug mode on macos due to small default thread stack size
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_pandas.py:<n>: pandas uses string dtype and not object dtype, keyword has no effect
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires scipy
skipped [<n>] test_sparse_tensor.py:<n>: requires sparse
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_table.py:<n>: could not import 'pyarrow.cuda': no module named 'pyarrow._cuda'
skipped [<n>] test_types.py:<n>: zoneinfo supports lower-case names on this platform
skipped [<n>] test_util.py:<n>: timezone database is already provided.
skipped [<n>] conftest.py:<n>: nonumpy not enabled
skipped [<n>] test_util.py:<n>: python version does not have the bug we're testing for
skipped [<n>] test_misc.py:<n>: condition: sys.platform != "win<n>"
= <n> failed, <n> passed, <n> skipped, <n> xfailed, <n> xpassed, <n> warnings in <n>.<n>s (<n>:<n>:<n>) =
process completed with exit code <n>.
```

**verdict: ___**

## 29. mpv-player/mpv · regression_weak

- incident `debd01a15aa3` · 2026-10-26 23:03 UTC · 1 job(s) · https://github.com/mpv-player/mpv/actions/runs/40416996622/job/121901713642
- job: `win32 (aarch64-pc-windows-msvc, arm64, windows-11-arm)`
- failed steps: Install Winget on windows-11-arm
- Gemini likely_cause: The CI job failed during the 'Install Winget' step due to an issue accessing the package repository or network/dependency download problem.
- fix commit(s):
- https://github.com/mpv-player/mpv/commit/c6e865576ccf6d9230a52c3e2ded742d257aeb5e (fix run https://github.com/mpv-player/mpv/actions/runs/40480206771)
- touched files: DOCS/man/options.rst, options/options.c, options/options.h, player/core.h, player/loadfile.c, player/playloop.c, video/out/d3d11/context.c, video/out/opengl/context_angle.c

Failure region (last 25 normalized lines):

```
note: switching to 'merge'.
you are in 'detached head' state. you can look around, make experimental
changes and commit them, and you can discard any commits you make in this
state without impacting any branches by switching back to a branch.
if you want to create a new branch to retain commits you create, you may
do so (now or later) by using -c with the switch command. example:
git switch -c <new-branch-name>
or undo this operation with:
git switch -
turn off this advice by setting config variable advice.detachedhead to false
head is now at <hex> merge <hex> into <hex>
##[endgroup]
[command]"program git.exe" log -<n> --format=%h
<hex>
cache hit for restore-key: aarch<n>-pc-windows-msvc-<hex>
received <hex> of <hex> (<n>.<n>%), <n>.<n> sec
received <hex> of <hex> (<n>.<n>%), <n>.<n> sec
received <hex> of <hex> (<n>.<n>%), <n>.<n> sec
cache size: ~<n> mb (<hex> b)
[command]"program tar.exe" -xf _temp/<uuid>cache.tzst -p -c mpv --force-local --use-compress-program "zstd -d"
cache restored successfully
cache restored from key: aarch<n>-pc-windows-msvc-<hex>
get-packagesource: unable to find repository 'psgallery'. use get-psrepository to see all available repositories.
process completed with exit code <n>.
```

**verdict: ___**

## 30. apache/arrow · regression_weak

- incident `af1dac57becc` · 2026-10-27 02:08 UTC · 3 job(s) · https://github.com/apache/arrow/actions/runs/40436665965/job/121966846711
- job: `AMD64 Conda C++ AVX2`
- failed steps: Execute Docker Build
- Gemini likely_cause: Docker build or network issue during container image setup or dependency fetching in the CI environment.
- fix commit(s):
- https://github.com/apache/arrow/commit/47578383648e09535213ee9598ba250ded672037 (fix run https://github.com/apache/arrow/actions/runs/40447744000)
- https://github.com/apache/arrow/commit/b17638caf5265b378d3a5864e3814a5cfaf7f75c (fix run https://github.com/apache/arrow/actions/runs/40445785435)
- touched files: cpp/src/gandiva/decimal_ir.cc, cpp/src/gandiva/llvm_generator_test.cc

Failure region (last 25 normalized lines):

```
pandas: latest
python: <n>.<n>
python_abi_tag: cp<n>
python_image_tag: <n>.<n>
python_wheel_windows_image_revision: <n>-<n>-<n>
python_wheel_windows_test_image_revision: <n>-<n>-<n>
r: <n>.<n>
repo: arrow-dev
r_custom_ccache: false
r_image: ubuntu-release
r_org: rhub
r_prune_deps: false
r_tag: latest
spark: master
tz: utc
ubuntu: <n>.<n>
ulimit_core: -<n>
vcpkg: <hex>
archery was called with:
export arch=amd<n>
export clang_tools=<n>
export docker_volume_prefix=.docker/
export llvm=<n>
export ubuntu=<n>.<n>
process completed with exit code <n>.
```

**verdict: ___**

