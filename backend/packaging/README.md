# Downstream wheel metadata correction

This is a packaging-only correction for the two pinned official archives in
wheel-pins.json, not a dependency upgrade or a change to native/app code.
Application requirements remain byte-for-byte unchanged from main
0854ac9210d6a9a450fc775dfe01c1fcadf666ac.

The original MediaPipe 0.10.31 WHEEL declares cp39/cp39 despite a py3/none
filename. Its ctypes-loaded x86-64 ELF has no Python symbols and requires at
most GLIBC_2.27. The conservative corrected tag is py3-none-linux_x86_64.
This does not claim a newly audited manylinux compatibility policy.
The XGBoost 1.7.6 WHEEL declares cp310/cp310 despite a py3/none filename;
its ctypes-loaded x86-64 ELF has no Python symbols and requires at most
GLIBC_2.17. Both original manylinux platform tags are retained. Ubuntu 24.04
native library resolution was verified separately; packaging checks do not
replace actual native smoke tests or production prediction parity tests.

Both derived archives carry Build: 1cricksy and matching filename build tags.
Only WHEEL and RECORD bytes change. METADATA (including dependencies and
versions), licenses, Python code, native libraries, and all other members are
byte-identical. Original file permissions and ZIP external/internal attributes are
preserved. ZIP ordering and timestamps are normalized; compression reproducibility is tested under the same interpreter
and zlib, not asserted across different compressor versions.

The helper pins official file URLs, SHA256 values and sizes, validates every
original RECORD entry, and verifies every derived member after writing.
MediaPipe has exactly one known original RECORD defect: the recorded native
filename libmediapipe_c_lib.cpython-39-x86_64-linux-gnu.so does not exist; its
actual name is libmediapipe.so. The exception requires the hardcoded original
path, actual path, size 28638200, and SHA256
715145a5556c567f4603c7f329e2c7382aba0123ac76b90108f64f8843e20639.
No other missing entry is accepted. Derived RECORD uses the actual name.

Run helper-only tests (no dependencies or downloaded wheel code executed):

    python -B -m unittest discover -s backend/tests -p test_wheel_metadata_repair.py -v

Create repaired wheels from downloaded pinned originals, or omit --originals
for hash-verified official HTTPS downloads:

    python backend/packaging/repair_wheels.py --originals ORIGINALS --output NEW_OUTPUT

Docker installs explicit derived local paths together with the original
requirements, retaining normal dependency resolution and pip check. Ubuntu
venv bootstrap wheels stay in the dependency stage. Only the venv and concise
wheel-provenance.json cross into the final runtime; wheel archives do not.
The final image exposes /opt/wheel-provenance.json for release audit.
No vulnerability gate is disabled, no workflow is modified, and no installed
metadata is edited in place. Build and deployment require separate validation.
