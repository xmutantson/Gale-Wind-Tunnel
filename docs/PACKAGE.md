# CAD package handoff

## What is supplied

The starting archive at commit `28f5cb1eba9e76fc25451888e091891cae75fe03` contains 36 Inventor parts, seven assemblies, an active project, a historical project backup, one STEP export, and a Pack and Go log dated July 3, 2023. The log records 44 native files; only 43 are supplied. The missing file is `Wind Tunnel Test Section Top.ipt` (log line 52).

The current validator reports that mismatch as an error. It does not waive it as a known issue. The STEP contains the top as an assembly occurrence and product, but that is not evidence that the native package is complete.

| Entry | Intended use and current limitation |
| --- | --- |
| `Main With Subparts.ipj` / `Main With Subparts.iam` | Native opening entry point; dependencies and installed resources need verification. |
| `Test Section Assembly.iam` | Test-section subassembly; contains a reference to the missing top part. |
| `Wind Tunnel Settling Chamber.iam` / `Wind Tunnel Settling Chamber As-Built.iam` | Two supplied variants; confirm which applies to the desired physical configuration. |
| `Wind Tunnel Exhaust Frame As-built.iam` | Supplied exhaust-frame assembly; the filename alone is not dimensional verification. |
| `Computer Box Assembly Rev2.iam` / `PowerBoardAssembly.iam` | Enclosure assemblies; electronics schematics, firmware and purchased-component specifications are not included. |
| `Main With Subparts.stp` | Neutral snapshot exported July 3, 2023; AP214, originating system Inventor 2024. |

The STEP root product identifier is `Wind Tunnel Inlet Test Assembly (To Simulate)` and its product name is `Main With Subparts`. Files labeled `Graphic Only`, `Mockup`, `Proto 1` and `As-Built` coexist. These names do not establish which geometry should be manufactured. Before a release, identify the intended assembly state, reference-only components and applicable variants explicitly. Do not move or rename native files without updating and checking their references in CAD.

## Restore and open the native package

1. Work on a separate copy. Activate the supplied IPJ and open the main IAM in an appropriate Inventor installation. Record the actual version used; no clean-machine opening test is documented yet.
2. Recover `Wind Tunnel Test Section Top.ipt` from the original project or a verified backup. Do not substitute an unrelated file with the same name. If only STEP-based reconstruction is possible, document it as a new reconstructed part and validate its geometry and assembly relationships in Inventor.
3. Resolve component references using the package copy, not the original author's external directories. A successful open on the original machine alone is insufficient evidence of portability.
4. Inspect the project's configured resources. `Main With Subparts.ipj` names `Design Data/Materials/InventorMaterialLibrary.adsklib` for both appearance and physical materials, plus `Templates`, `Presets` and `ContentCenter`. These resources are absent. Determine which installed libraries or project-specific resources are actually required before adjusting paths; do not replace material assignments merely to silence warnings.
5. Rebuild the intended assembly, examine unresolved references and component/material properties, and compare it with the physical configuration where available. Record findings and any substitutions.

The repository cannot currently supply a complete fabrication procedure. Before building, prepare a BOM with part/assembly ID, revision, quantity, material, stock dimensions, manufacturing process, purchased-part specification and source. Produce drawings for the fabricated parts with units, critical dimensions, tolerances and assembly interfaces. Determine actual fan, motor and sensor specifications rather than deriving them from mockup geometry or filenames.

The README describes approximately 17,000 ten-inch straws in the inlet. They are not modeled. Document their diameter, packing, retention and installation, and include the flow conditioner in the BOM and assembly instructions. A representative envelope and a detailed specification may suffice; a model of every straw is not required to make this omission explicit.

## Automated checks and their limits

Run the commands in the [README](../README.md#check-the-package-offline) from the repository root. No dependencies need installation. The tests create and remove temporary fixture directories; native fixture files are deliberately not real CAD models. `-B` avoids Python bytecode files.

The validator checks:

- A readable, flattened `packngo.log`, its declared versus listed native-file count, duplicate basenames, and presence of listed files. Extra native files are reported for review. The log is a historical manifest, **not** a live Inventor dependency graph. New designs require a fresh dependency check and manifest.
- Readable Inventor project XML and existence of configured relative resource paths. External paths are flagged without looking them up. Absence of a resource is a warning because its runtime impact depends on the CAD installation.
- STEP opening/closing and section markers, entity definitions, duplicate IDs and undefined numeric references. Quoted strings, doubled quotes and comments are masked before looking for entities. Unterminated strings/comments fail the check. This is a limited text check for this single-DATA-section export, not a STEP grammar parser or CAD kernel.
- Nonempty native/project/STEP assets, with sizes and SHA-256 hashes in JSON output. A nonempty native file is not necessarily valid CAD; the fixture tests intentionally demonstrate this boundary.

For the unchanged supplied assets, the STEP text check finds 123,852 entity definitions, 40 product records, 82 assembly occurrences and 35 manifold-solid records. These are baseline observations, not hard-coded acceptance thresholds; legitimate design changes can change them. The current validator inventories 45 assets (43 native files, IPJ and STEP), reports one missing-part error and four resource warnings.

Hash inventory records file identity, not correctness. The validator never repairs geometry, supplies a missing component or upgrades its findings to a claim of CAD import or physical validation.

## Release acceptance

Before labeling a new package reproducible:

1. Open and rebuild the intended assembly on a clean machine/profile without the author's source directories. Record Inventor version, configuration, resolved dependencies and material-library choices. Supply required resources or document installation prerequisites.
2. Refresh the flattened Pack and Go package and manifest. Run the validator and review every warning. Require zero errors; do not change the declared manifest count merely to hide a missing component.
3. Export the intended assembly to STEP. Record source revision, assembly state, CAD version and export settings. Independently import the export and compare component placement, key dimensions and expected geometry against the native design. STEP unit definitions include inches and millimeters; let the importer interpret them, then verify dimensions. The export's geometric precision is not a manufacturing tolerance specification.
4. Include the BOM, drawings, assembly instructions, configuration/variant list and known limitations. Record the resulting asset hashes with the release evidence. Document the author's chosen reuse and attribution terms without inferring new terms from the existing README.
5. Treat performance as a separate acceptance activity: record instrument models/calibration, measurement locations, operating settings, environmental conditions and repeated measurements. Publish raw data, calculation method, uncertainty and a defined operating envelope before making quantitative flow-quality claims. Choose acceptance thresholds from the intended use rather than inferring them from the CAD archive.

Remaining prerequisites are the original missing part or an explicitly validated reconstruction, access to CAD tools for native/import checks, manufacturing specifications, and physical measurements. The offline checks cannot replace these activities.
