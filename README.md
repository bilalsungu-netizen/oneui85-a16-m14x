# Galaxy M14 5G — A16 One UI 8.5 port preparation

**Status: source configuration and build automation prepared; no flashable ROM has been produced or boot-tested.**

## Verified firmware inputs

- Donor (Samsung Galaxy A16 5G, SM-A166B, TUR): `A166BXXSADZH1/A166BOXMADZH1/A166BXXSADZH1/A166BXXSADZH1` — Android 16, One UI 8.5.
- Target stock (Samsung Galaxy M14 5G, SM-M146B, TUR): `M146BXXSFDZI1/M146BOJMFDZI1/M146BXXSFDZI1/M146BXXSFDZI1` — Android 15, One UI 7.0; U15 / Binary F.
- Port engine: [KrrishJaat/ReCoreUI](https://github.com/KrrishJaat/ReCoreUI), branch `8.5` (MIT licensed).
- This project deliberately does **not** import S24 FE firmware or optional donor packages.

## What this package changes

1. ReCoreUI `objectives/m14x/m14x.sh` — pins A16 TUR donor and M14 TUR stock.
2. Removes any optional S24 FE firmware model from the configuration.
3. Adjusts the upstream downloader to pin **stock** firmware too (otherwise it silently selects the latest stock).
4. Retains the M14 stock AP archive long enough to extract the target boot-chain images.
5. Removes the `platform/m14x/KernelSU-Next` manager APK preload, and substitutes a build-stage script that stages **unmodified M14 stock** boot, vendor_boot, dtbo and vbmeta images.
6. GitHub Actions: optional `preflight` or **explicitly selected** experimental `build` mode. No firmware is published as public Actions artifacts.

**Caution:** Removing an APK does not itself unroot a kernel. The kernel replacement is an attempt to avoid shipping the ReCoreUI prebuilt kernel; rootlessness has **not** been independently verified against built images. A stock vbmeta can reject a modified `super` partition. This project does **not** bypass AVB or claim that the resulting ZIP can boot.

## Adding this to the GitHub repository

Suggested destination: `bilalsungu-netizen/M14-OneUI9-Port`, preferably a new branch `oneui85-a16-m14x` to preserve existing Android 17 work.

If GitHub connection rejects branch/file writes (403), you can use the **single-file** workflow `M14_A16_OneUI85_Tek_Dosya_Workflow.yml`: create `.github/workflows/m14-a16-oneui85.yml` on GitHub and paste its entire contents. No separate Python file is needed.

Alternatively, add these **two modular files** manually on GitHub:
- `tools/prepare_recoreui.py`
- `.github/workflows/m14-a16-oneui85.yml`

In the web UI, choose **Add file → Create new file**, enter the complete path and paste the matching file content. Create a new branch if possible. Push neither Samsung firmware nor personal/device identifiers into Git.

Then go to **Actions → M14 A16 One UI 8.5 experimental port → Run workflow** and keep `mode=preflight`. On success, inspect the output log. The `build` option intentionally starts a large, **experimental** build and can fail; it does not produce an approved installation package. To retrieve large outputs, configure a **GitHub Actions secret** named `GOFILE_TOKEN` (and optionally `GOFILE_FOLDER_ID`). The workflow uploads through the Gofile API, splitting files into parts of up to 4,500 MiB. With no secret, the build candidate remains on the temporary runner and cannot be downloaded afterward. The `m14-a16-oneui85-preflight` artifact contains upload status/links.

## Reproducing locally

```bash
git clone --depth 1 --branch 8.5 https://github.com/KrrishJaat/ReCoreUI.git ReCoreUI
python3 tools/prepare_recoreui.py ReCoreUI
python3 tools/prepare_recoreui.py ReCoreUI --check-only
# For an intentionally experimental, externally provisioned build host:
# cd ReCoreUI && sudo bash build.sh --build m14x
```

Build-host prerequisites (package installation, firmware downloader, privileges and storage) are managed primarily by upstream ReCoreUI. Firmware downloads require a working Samsung FUS/samloader path; regional availability and CI duration are not guaranteed.

## Tests still required

- Firmware download and unpack, VINTF manifest/framework compatibility.
- SELinux `neverallow` conflicts and runtime denials (avoid blanket permissive patches).
- Actual `boot.img` and `vbmeta.img` signatures/AVB strategy; recovery compatibility.
- IMS/VoLTE/VoWiFi, auto brightness, fingerprint, camera, 90 Hz and performance on device.
- Root detection and expected app functionality before any daily-driver use.

**Never flash A16 BL/CP/CSC via Odin to the M14. Do not flash an unverified candidate without full stock recovery files and backups.**

## Provenance

[ReCoreUI](https://github.com/KrrishJaat/ReCoreUI) scripts are fetched at runtime; the original source and licensing remain credited. No upstream proprietary APKs, firmware or kernel images are distributed here.

Firmware checks:
- [Samsung A16 5G update page](https://doc.samsungmobile.com/SM-A166B/031022241021/tur.html)
- [Samsung A16 donor package information](https://samfota.com/firmware/sm-a166b/euy/a166bxxsadzh1/)
- [M14 TUR stock firmware](https://samfota.com/ar/firmware/sm-m146b/tur/m146bxxsfdzi1/)
