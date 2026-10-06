Native Workbench 0.8.0 — application and tool packs

Extract this complete folder to a location you can write to, then open
NativeWorkbench.exe. The interface is a native Windows application.

The starter includes minimap2 for alignment, samtools for alignment processing,
and bcftools for variant calling. Each task can run alone or in a connected
pipeline. Choose the example pipeline to try the bundled tiny scientific data.

Use the pack manager to import a downloaded pack ZIP or browse a configured
publisher catalogue. A catalogue must be explicitly configured before online
packs are shown; this build does not invent a live download service. Downloaded
packs are verified and installed into their own versioned folders. Local pack
folder import remains available for disconnected installations.

Application updates and pack installation are separate. Updating the application
does not replace optional packs, user settings or analysis results. Pack archives
carry their declared executables, private runtimes, scientific metadata, tests and
licenses. Running installed tools remains local and works without a network.

Use References to discover and download public reference files. Each completed
download is kept locally with provider, release, assembly, URL and checksums.
Reference downloads are explicit network operations; analysis files are not
uploaded. References are separate from the application and optional tool packs.

Choose File > Check installation to check the core and installed pack fixtures.
See SOURCE-AVAILABILITY.json for the separately distributed application source
archive and exact pack/source companions. Application and private Python licenses
are installed. Native MinGW-w64, winpthreads and LLVM notices are in
runtime/licenses/native; tool licenses and source notices remain within each pack.

This development build has not been executed on native Windows in its build
workspace. Run the installation checks on your Windows machine.
