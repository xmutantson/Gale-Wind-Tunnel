# Gale-Wind-Tunnel
This is the CAD associated with a prototype wind tunnel. I included a STP file for those not in the autodesk ecosystem.

This project was a very long ~2 year undergraduate project for my Mechanical Engineering degree. This was a solo project, so I didn't have help from my classmates but I did have a lot of help from Confluent makerspace. The physical design is from "Low Speed Wind Tunnel Testing" by Barlow, Rae, and Pope. It has proven to be a very good design. The only thing not included/modeled in this repo is that the inlet box is full of 10" drinking straws to create a laminar flow (~17k of them). The overall tunnel is approximately 9.5 feet long.

If you have any questions, contact me (email on my profile). This design is fully open source, no copyrights but attribution if using these specific files.

## Package status

This repository is a prototype CAD archive, not a complete fabrication or validated performance package. The original project description above records the author's experience; measured flow quality, calibration data and an operating envelope are not supplied here.

**Known missing component:** `Wind Tunnel Test Section Top.ipt` is listed in `packngo.log` and referenced by `Test Section Assembly.iam`, but is absent from this repository. The STEP export contains a component with that name. Restoring the original native part and verifying the assembly in Inventor remain necessary; the STEP export does not restore the original feature history.

The project also points to an absent material library and absent Templates, Presets and ContentCenter folders. Their impact depends on the Inventor installation. See [setup, configuration and release checks](docs/PACKAGE.md) before changing project settings or fabricating parts.

## Open the design

- **Neutral CAD:** import [`Main With Subparts.stp`](Main%20With%20Subparts.stp) into a STEP-capable CAD application. It is an AP214 export whose header identifies Autodesk Inventor 2024. Confirm units, key dimensions and components after import; successful import has not been verified by the automated checks.
- **Native Inventor:** activate [`Main With Subparts.ipj`](Main%20With%20Subparts.ipj), then open [`Main With Subparts.iam`](Main%20With%20Subparts.iam). Resolve the known missing part before treating the package as complete. The export header identifies the source version, not a tested compatibility range for all files.

Keep the shipped filenames and flat layout while resolving references. `Main With Subparts.ipj.old` is a historical project file, not the documented entry point.

## Check the package offline

From the repository root, with Python 3.11 or newer:

```text
python -B tools/validate_package.py
python -B tools/validate_package.py --json
python -B -m unittest discover -s tests -v
```

The validator uses only Python's standard library. It reads package files and prints findings; it does not launch CAD, access the network or change files. JSON output includes a SHA-256 inventory of native CAD files, the project and the STEP export. `--root PATH` checks another copy of the same package layout.

Exit code **1** means a package error was found; **0** means these limited checks found no errors. Missing configured project resources are warnings. The current archive is expected to return **1** for the missing top part, with four resource warnings. The regression tests use temporary fixtures and are expected to pass independently of that known archive defect.

Checks cover the historical Pack and Go manifest, project resource paths and basic STEP text consistency. They do **not** discover every native dependency, validate full STEP grammar or geometry, certify materials or manufacturing tolerances, or establish wind-tunnel performance.
