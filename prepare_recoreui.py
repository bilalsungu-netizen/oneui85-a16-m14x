#!/usr/bin/env python3
"""Apply a minimal, reviewable A16 One UI 8.5 donor conversion to ReCoreUI 8.5.

This prepares an experimental build. It does NOT validate boot, AVB or IMS.
Upstream project: https://github.com/KrrishJaat/ReCoreUI (MIT license).
"""
from pathlib import Path
import argparse
import re
import sys

DONOR = "A166BXXSADZH1/A166BOXMADZH1/A166BXXSADZH1/A166BXXSADZH1"
STOCK = "M146BXXSFDZI1/M146BOJMFDZI1/M146BXXSFDZI1/M146BXXSFDZI1"

# Use the M14's UNMODIFIED, model-matched boot chain rather than the
# potentially root-enabled prebuilt boot images supplied by the port framework.
KERNEL_SCRIPT = r'''#!/usr/bin/env bash
# Experimental: take boot chain exclusively from the M14's stock AP package.
# NOTE: stock vbmeta may reject the modified system. Do not flash until
# AVB, kernel/system compatibility and rollback/recovery are audited.
# This script is sourced by the ReCoreUI builder: do not change shell options.
AP_DIR="${FW_BASE}/${STOCK_MODEL}_${STOCK_CSC}"
AP="$(find "$AP_DIR" -maxdepth 1 -type f \( -name 'AP_*.tar.md5' -o -name 'AP_*.tar' \) -print -quit)"
[[ -n "${AP:-}" && -s "$AP" ]] || { echo "Stock M14 AP archive missing"; return 1; }

mkdir -p "$DIROUT"
for PART in boot vendor_boot dtbo vbmeta; do
  ENTRY="$(tar -tf "$AP" | grep -E "(^|/)${PART}\.img\.lz4$" | head -n 1 || true)"
  [[ -n "$ENTRY" ]] || { echo "Missing ${PART}.img.lz4 in stock AP"; return 1; }
  TMP="$DIROUT/${PART}.img.tmp"
  rm -f "$TMP"
  if ! tar -xOf "$AP" "$ENTRY" | lz4 -dc > "$TMP"; then
    echo "Decompression failed: ${PART}.img"
    return 1
  fi
  [[ -s "$TMP" ]] || { echo "Empty ${PART}.img"; return 1; }
  mv -f "$TMP" "$DIROUT/${PART}.img"
done
printf '%s\n' "Stock M14 boot components staged; AVB not validated."
'''

def replace_assignment(s: str, key: str, value: str, required=True) -> str:
    pattern = rf'(?m)^[ \t]*{re.escape(key)}="[^"\n]*"[ \t]*(?:#.*)?$'
    replacement = f'{key}="{value}"'
    if re.search(pattern, s):
        return re.sub(pattern, lambda _: replacement, s, count=1)
    if required:
        raise ValueError(f"Upstream structure changed: {key} missing")
    return s.rstrip() + "\n" + replacement + "\n"

def apply(repo: Path):
    required = [
        "build.sh", "objectives/m14x/m14x.sh",
        "scripts/utils/download_utils.sh", "scripts/unpack_fw.sh",
        "platform/m14x/kernel.sh",
    ]
    missing = [p for p in required if not (repo / p).is_file()]
    if missing:
        raise FileNotFoundError("ReCoreUI 8.5 tree missing: " + ", ".join(missing))

    config = repo / "objectives/m14x/m14x.sh"
    s = config.read_text()
    for key, value in (
        ("MODEL", "SM-A166B"), ("CSC", "TUR"),
        ("PORT_FIRMWARE", DONOR),
        ("STOCK_MODEL", "SM-M146B"), ("STOCK_CSC", "TUR"),
        ("EXTRA_MODEL", ""), ("EXTRA_CSC", ""), ("EXTRA_FIRMWARE", ""),
        ("FILESYSTEM", "erofs"),
    ):
        s = replace_assignment(s, key, value)
    s = replace_assignment(s, "STOCK_FIRMWARE", STOCK, required=False)
    config.write_text(s)

    downloader = repo / "scripts/utils/download_utils.sh"
    s = downloader.read_text()
    needle = '    elif [[ "${FW_PREFIX,,}" == "extra" ]]; then\n        REQUESTED_VERSION="$EXTRA_VERSION"'
    if "REQUESTED_VERSION=\"${STOCK_FIRMWARE:-}\"" not in s:
        if needle not in s:
            raise ValueError("download_utils.sh: unexpected FETCH_FW structure")
        s = s.replace(needle, needle + '\n    elif [[ "${FW_PREFIX,,}" == "stock" ]]; then\n        REQUESTED_VERSION="${STOCK_FIRMWARE:-}"', 1)
    downloader.write_text(s)

    unpacker = repo / "scripts/unpack_fw.sh"
    s = unpacker.read_text()
    old = 'if IS_GITHUB_ACTIONS; then rm -f "$AP_PACKAGE" && rm -rf "$SOURCE_DIR"; fi'
    new = 'if IS_GITHUB_ACTIONS && [[ "$FW_TYPE" != "stock" ]]; then rm -f "$AP_PACKAGE" && rm -rf "$SOURCE_DIR"; fi'
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise ValueError("unpack_fw.sh: unexpected AP cleanup structure")
    unpacker.write_text(s)

    # Avoid bundling the root manager APK. The remaining ROM must still be
    # independently audited for any other root mechanism.
    ksu_dir = repo / "platform/m14x/KernelSU-Next"
    if ksu_dir.exists():
        import shutil
        shutil.rmtree(ksu_dir)
    (repo/"platform/m14x/kernel.sh").write_text(KERNEL_SCRIPT)

    print("CONFIGURED donor", DONOR)
    print("CONFIGURED stock", STOCK)
    print("Removed S24 FE optional donor and KernelSU-Next manager preload.")
    print("Prepared stock M14 boot chain extraction (not validated for AVB).")
    print("STATUS: EXPERIMENTAL SOURCE PATCH, NOT A VERIFIED FLASHABLE ROM.")

def check(repo: Path):
    s=(repo/"objectives/m14x/m14x.sh").read_text()
    expected={
        "MODEL":"SM-A166B","CSC":"TUR", "STOCK_MODEL":"SM-M146B",
        "STOCK_CSC":"TUR","PORT_FIRMWARE":DONOR,"STOCK_FIRMWARE":STOCK,
        "EXTRA_MODEL":"","FILESYSTEM":"erofs"
    }
    for k,v in expected.items():
        if not re.search(rf'(?m)^{k}="{re.escape(v)}"$',s):
            raise AssertionError(f"Incorrect {k}")
    assert not (repo/"platform/m14x/KernelSU-Next").exists(), "KernelSU preload still present"
    assert 'REQUESTED_VERSION="${STOCK_FIRMWARE:-}"' in (repo/"scripts/utils/download_utils.sh").read_text()
    assert '[[ "$FW_TYPE" != "stock" ]]' in (repo/"scripts/unpack_fw.sh").read_text()
    assert "Stock M14 AP archive missing" in (repo/"platform/m14x/kernel.sh").read_text()
    print("PASS: configuration checks; image/boot/IMS not tested")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("recoreui", type=Path, help="Checked-out ReCoreUI v8.5 root")
    parser.add_argument("--check-only", action="store_true")
    args=parser.parse_args()
    try:
        (check if args.check_only else apply)(args.recoreui.resolve())
    except (OSError, AssertionError, ValueError) as e:
        print("ERROR:",e,file=sys.stderr)
        sys.exit(1)
