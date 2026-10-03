# Native Workbench

Run bioinformatics tools locally on Windows through a native desktop application.
Choose files and folders, run a tool, or connect compatible tools into a branching
pipeline. Analysis data stays on the machine.

The small starter distribution includes **minimap2, SAMtools and BCFtools**.
Additional tools are installed as independently versioned packs through
**Manage tools**, either from an approved signed catalogue or an offline ZIP.
The application does not require Docker, WSL or a system Python installation.

## Release status

Version **0.6.0 is a development build**. Its application, updater and 18 pack
archives have been prepared. This repository has not yet published those assets
or an official signed catalogue. Do not treat proposed download URLs as live.

The build passed 214 automated tests with one Windows-only skip, the eight
starter installation/scientific checks, and an actual 0.5.4-to-0.6.0 updater
migration on Linux. Scientific execution used the portable Linux reference
backend. The new Windows GUI and native Windows long-path behavior still need
validation on Windows.

## Using the application

Once published, downloads will be on the
[Releases page](https://github.com/comparativechrono/workbench/releases).
Extract the starter ZIP and run `NativeWorkbench.exe`. Use
**File > Check installation** to check the target machine.

The separate updater requires an existing **0.5.4** installation. Close Workbench,
extract the updater outside the application folder, run `UpdateWorkbench.exe`,
and choose the existing `native-workbench` folder. Installed packs, saved settings
and results are retained.

Saved pipelines retain exact pack versions and manifest hashes. Installing a
newer pack does not silently change an existing pipeline. Methods descriptions,
pipeline diagrams and execution records accompany results.

## Development and independent packs

This repository contains application source and pack development tools. Large
executables, private runtimes, third-party source archives and pack ZIPs belong
in release assets, not Git history. Application and pack tags can be released
independently in this repository; a second repository is not required.

- [Pack development](docs/pack-development-0.6.md)
- [Signed catalogue publishing](docs/catalogue-publishing-0.6.md)
- [Repository-specific publishing plan](docs/github-publication.md)
- [Source recovery](docs/source-recovery/README.md)

Some build and scientific test paths require the separately distributed runtime
and source companions. This checkout alone is not the complete third-party
build environment. Keep the matching source companions available alongside
binary releases.

The application license is in [LICENSE](LICENSE). Third-party tools and runtimes
retain their respective licenses and notices.
