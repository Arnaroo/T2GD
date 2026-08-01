# T2GD 1.19.0 "Shenlong"

The first public release. It supersedes 1.18.0 "Fafnir" (2026-07-30), which was
built and tested but never distributed. Fafnir appears throughout these notes as
the reference build that 1.19.0 is checked against.

T2GD converts alignments made against a transcriptome FASTA into genome
coordinates, using a GTF annotation as the map, and ships 36 subcommands around
that core operation. See [CHANGELOG.md](CHANGELOG.md) for what is in the
release and [INSTALL.md](INSTALL.md) for how to install it.

## What is new in 1.19.0

Packaging and performance. No conversion, filtering or counting logic was
touched and **no record T2GD writes has changed**; the work is in how the
executables are linked and presented, how fast two hot paths run, and how the
program behaves against a low open file limit. The record-stream equivalence
gate against 1.18.0 is reported under **Determinism across platforms** below.

The command line surface is unchanged, with one exception on Windows, noted
below, where the command line moves to a second executable.

**The graphical interface no longer drags a terminal behind it.** On both
Windows and macOS, launching the GUI in the ordinary way used to open an empty
console or terminal window alongside it. Both are gone, by different means,
because the two platforms fail this in different ways.

* **Windows** now ships two executables. A Windows program declares at link
  time whether it owns a console and cannot answer both ways; the single
  `t2gd.exe` of 1.18.0 answered "yes", which is where the empty black window
  came from. `t2gd.exe` now answers "no", and the new `t2gd-cli.exe` carries
  the console for command line work. The subsystem flag is verified in the PE
  header, and launching `t2gd.exe` on a live Windows desktop was observed to
  open the interface with no console window. The consequence worth knowing is
  that `t2gd.exe --cli` has nowhere to print to; use `t2gd-cli.exe`, which sits
  in the same folder.
* **macOS** now ships `T2GD.app`. Finder does not launch a bare executable
  directly. It hands it to Terminal, which is why double-clicking `t2gd`
  produced a terminal with the interface running inside it. The bundle goes
  through the normal launch path instead. It also locates the GTK 3 runtime
  itself, in `/opt/homebrew/lib` or `/usr/local/lib`, and reports in a dialog
  if it is absent, because an app launched from Finder inherits the launchd
  environment rather than your shell's and a loader error would otherwise go
  somewhere you could not see it.

**The built-in manual now matches the shipped packaging.** The *Installing
T2GD* topic described a `t2gd-cli-static` binary and a `generic` build
variant, neither of which was ever in a release, claimed a macOS x86_64 build
that does not exist, and gave an unpack path that did not match the archives.
It was rewritten from the artifacts. The topic also stated that the GTK
dependency was optional at run time for `t2gd`; it is not, and the corrected
text says so.

**`depth` and `coverage` are about 3x faster.** They no longer thrash the
garbage collector on the per-reference column window, and the integer formatter
no longer performs a 64-bit hardware divide per digit. On a 175 MB nanopore BAM
emitting 316 M positions, `depth -t 1` goes from 51.8 s to 17.7 s. The larger
change is in work rather than wall clock: at `-t 8` the old build spent 215
CPU-seconds to buy 14 % of wall time over `-t 1`, and now spends 33. Output is
byte-for-byte identical to 1.18.0, verified across 12 fixtures by
`{default, -a, -aa}` by `{-t 1, 4, 8}`.

**BAM writing is about 1.9x faster.** BGZF compression now uses libdeflate
instead of zlib, which affects every subcommand that writes a BAM. `sort -t 8
--bgzf-threads 8 --read-threads 8` on a 175 MB BAM goes from 4.85 s to 2.42 s.
libdeflate is statically linked; the shared library list is unchanged.

**The compressed bytes differ from 1.18.0 but the records do not.** This is the
one change here that can be seen from outside. libdeflate and zlib both emit
valid DEFLATE and make different, equally legal choices, so file size shifts by
about a percent and **the direction depends on the data**: 1.2 % smaller on one
sort output, 1.1 % larger on the demo conversion. Budget for a percent either
way rather than for a saving. If you have pinned a checksum of a **BAM file**
it will change; a checksum of `samtools view` output will not. Use
`t2gd checksum`, which is content-based and order-agnostic, if you need to
prove two BAMs hold the same records.

**Open file limits are handled rather than documented around.** The disk-spill
merge opens one descriptor per spill batch, and that count scales with the
number of batches rather than with the size of the input, so under the common
soft limit of 1024 a convert could die at roughly 500,000 records on a file of
only a few hundred MB. This was reported from the field. T2GD now raises its
own soft limit to the hard limit at start-up, which is the opt-in that the
split between a low soft limit and a high hard limit exists to allow, and is a
no-op where the two are equal. Where the hard limit genuinely is low, raising
the soft limit cannot help, so the merge also checks the descriptor budget
before opening anything and fails with a message naming the knobs to change,
rather than surfacing `Too many open files` partway through.

Note that the copy of `CHANGELOG.md` inside the archives predates that last
item and does not describe it. The behaviour is in the shipped binaries; only
its description was late. `USAGE.md` in the repository is correct.

## Artifacts

| Platform | Archive | Size | Binaries |
|---|---|---:|---|
| Linux x86_64, znver4 | `t2gd-1.19.0-Shenlong-linux-x86_64-znver4.tar.gz` | 5,603,633 | `t2gd`, `t2gd-cli` |
| Linux x86_64, znver2 | `t2gd-1.19.0-Shenlong-linux-x86_64-znver2.tar.gz` | 5,465,621 | `t2gd`, `t2gd-cli` |
| Linux x86_64, broadwell | `t2gd-1.19.0-Shenlong-linux-x86_64-broadwell.tar.gz` | 5,538,852 | `t2gd`, `t2gd-cli` |
| macOS arm64 | `t2gd-1.19.0-Shenlong-macos-arm64.tar.gz` | 6,152,835 | `T2GD.app`, `t2gd`, `t2gd-cli` |
| Windows x86_64 | `t2gd-1.19.0-Shenlong-windows-x86_64.zip` | 27,063,486 | `t2gd.exe`, `t2gd-cli.exe` |

Sizes are bytes.

**Which one.** If you are unsure, take `broadwell`; it runs everywhere the
other two Linux builds do. `znver4` needs AVX-512, so AMD Zen 4 or newer.
`znver2` needs AMD Zen 2 or newer. The macOS build is Apple Silicon only and
needs macOS 14 or newer. The Windows build runs on any x86-64 machine with
Windows 10 or newer.

**Which binary.** `t2gd` is the full build and runs headless as
`t2gd --cli <subcommand>`. `t2gd-cli` contains no graphical code at all and is
the binary to use on HPC nodes and in containers. On macOS, use `t2gd-cli` for
command line work: the full binary looks for GTK at startup and macOS has no
system wide search path that finds a Homebrew install.

Windows ships the same pair, `t2gd.exe` and `t2gd-cli.exe`, for a different
reason: a Windows program declares at link time whether it owns a console, so
the graphical build cannot also be the command line build without dragging an
empty console window along behind the interface. Use `t2gd-cli.exe` on the
command line. The Windows archive is larger because the GTK 3 runtime travels
inside it; keep the folder together, since moving `t2gd.exe` out on its own
breaks the graphical interface. `t2gd-cli.exe` needs nothing from the folder.

## Checksums

SHA-256 of the release archives. These are also in `SHA256SUMS` alongside the
archives.

```
287efd1ba5e4094b8ab1dcd7e7e698696a93de4a332a13fb8f08221540c141bf  t2gd-1.19.0-Shenlong-linux-x86_64-znver4.tar.gz
5a13c2686408c113dd0a30b3322a03c335128743aa76401e2e2b8d264020c7f1  t2gd-1.19.0-Shenlong-linux-x86_64-znver2.tar.gz
1f0c9a0369e9db8cf48bb4a6c680194ece57c282b5a9c8f54e8bb4fe4c8f344a  t2gd-1.19.0-Shenlong-linux-x86_64-broadwell.tar.gz
a81da462a43d62ebc8f64d56d37344622b55f059e426e60071be5493a66a59e8  t2gd-1.19.0-Shenlong-macos-arm64.tar.gz
fa182f9139b2408a3d09107bd0d0a8aa5e22e3731304967bf9236ff422bdbc2a  t2gd-1.19.0-Shenlong-windows-x86_64.zip
```

Verify a download:

```sh
sha256sum -c SHA256SUMS --ignore-missing
```

On macOS, `shasum -a 256 -c SHA256SUMS --ignore-missing`. On Windows,
`certutil -hashfile t2gd-1.19.0-Shenlong-windows-x86_64.zip SHA256`.

SHA-256 of the executables themselves, after unpacking. Each archive also
carries its own `SHA256SUMS`, which you can check from inside the unpacked
folder.

```
2e76d5048a23a18730655367bc212582a12be255ebb8a024783efb15166b8468  linux-znver4/t2gd
5cbcaad8c4399f7f8de7da35e40db50d17a80a6053700b90e44e6918a8244767  linux-znver4/t2gd-cli
9d80ea905a0cb10423f7838c6af8c334e828d92f8a7cd2d95f0d946384957068  linux-znver2/t2gd
d8faaf504fd98bccd404c136511989425681b7023a4321a128b1d8f0f17222e0  linux-znver2/t2gd-cli
598ff57f71f0921101fb7a4e62dfe3fac3e75b53cdff10c59dad44f929eeb6d4  linux-broadwell/t2gd
154d385ac7c7a122fae5603ef1a32724c312fe3dff973c0a51a962858d7e98e2  linux-broadwell/t2gd-cli
ff62a33d42643492f3c29d26763248803647697c99c150d89366d2f20cc351d5  macos-arm64/t2gd
a9f920f6d767eccdade0576ac89347d21279eac968f94e77caa89003de6b60a6  macos-arm64/t2gd-cli
9c70c063740e38af9fdd612f8469c6289c51fa11e170ce9ca515d53e8dacfaa3  macos-arm64/T2GD.app/Contents/MacOS/T2GD
8db8f0ef286c1f4a866193a66f5d5d6aaae19febf48728a2925c8d775ce6d2fd  macos-arm64/T2GD.app/Contents/MacOS/t2gd-bin
cd86de8249590d97552000e2236ad45ae778e4aad4a4b3dcc384b52152bfe7be  windows-x64/t2gd.exe
6fbe44721888a66446078e98a5c44d63f70b5ff6fb599a5ccffd082bb6824598  windows-x64/t2gd-cli.exe
```

Two of those lines deserve a note. `T2GD.app/Contents/MacOS/t2gd-bin` is the
same build as the bare `macos-arm64/t2gd` but does not hash the same and is 16
bytes larger, because ad-hoc signing the bundle rewrote the signature blob
inside it. `T2GD.app/Contents/MacOS/T2GD` is not a build at all; it is the
small launcher script that finds the GTK runtime and then execs `t2gd-bin`.

## What is in each archive

Every archive contains the binaries, plus:

| File | What it is |
|---|---|
| `README.md` | Start here. What the tool is and the one command that runs it. |
| `CHANGELOG.md` | What is in this release. |
| `LICENSE.txt` | CC BY-NC-ND 4.0, with a plain-language summary. |
| `RUN_LINUX.txt`, `RUN_MACOS.txt` or `RUN_WINDOWS.txt` | Platform-specific first-run notes. |
| `SHA256SUMS` | Checksums for the binaries and the documents listed above. |

`SHA256SUMS` covers the executables and the four documents. On Windows it does
not cover the bundled GTK runtime, which is 897 further files; those are
covered by the checksum of the archive as a whole.

The Windows archive additionally carries that runtime: 47 DLLs beside
`t2gd.exe`, the gdk-pixbuf loaders under `lib\` (15 files), and themes and
icons under `share\` (834 files), 903 files in the archive altogether. Nothing
needs installing and no environment variable is required, because Windows
searches the executable's own directory first. `t2gd-cli.exe` needs none of it
and runs on its own.

The macOS archive additionally carries `T2GD.app`. Open that rather than
double-clicking the bare `t2gd`: Finder hands a bare executable to Terminal,
so the bundle is what makes the interface open without one.

The manual is inside the executable. Nothing is fetched at runtime and nothing
is installed alongside, so `t2gd help` works on a machine with no network.

## Dependencies

None beyond the platform system libraries. The D runtime and libdeflate are
linked in.

On Linux, `readelf -d` NEEDED lists only `libz`, `libm`, `libgcc_s`, `libc` and
`ld-linux`. On macOS, `otool -L` lists only `libz`, `libSystem` and `libobjc`,
all from `/usr/lib`, with no Homebrew path baked in and no `LC_RPATH`. On
Windows the import table lists only `KERNEL32.dll`, `ADVAPI32.dll` and
`WS2_32.dll`.

GTK 3 is absent from the link record on every platform, including in the full
build, because the toolkit is loaded at startup rather than linked. That is a
runtime load, not a weak link, so the full binary still needs GTK present at
startup even when you run it as `t2gd --cli`. The binary that needs no GTK at
all is `t2gd-cli`, which contains no graphical code.

## Determinism across platforms

Every platform produces the same records from the same input. This is verified
on each release by comparing the record stream checksum of the same conversion
run on each build; the table below gives what was run for 1.19.0. A result
therefore does not change when you move machines.

Because 1.19.0 changes no conversion code, the record stream it produces should
match 1.18.0 exactly. That is checked rather than assumed. Two conversions were
run under 1.19.0 and their record stream checksums compared against the values
recorded for 1.18.0:

| Reference conversion | Records | 1.18.0 | 1.19.0 |
|---|---:|---|---|
| Demo (`tests/demo`, GRCh38 subset) | 59,886 | `34d6da6cd0356bd924d7381a3b4b2d23` | same |
| SUDHL8 short-read, GRCh38.114 | 5,781,316 | `0fa6ed91f920987b02b4421c40e183e8` | same |

Both match. Note that the *files* are not identical and are not meant to be:
the `@PG` header line records the invoking command and the version that ran it,
so a header comparison would differ by design. The gate is on records only.

What was run against the demo value for this release, exactly:

| Build | Binary | Result |
|---|---|---|
| linux-znver2 | `t2gd-cli`, and `t2gd --cli` | match |
| linux-broadwell | `t2gd-cli`, and `t2gd --cli` | match |
| linux-broadwell, unpacked from the tarball | `t2gd-cli` | match |
| windows-x64, under wine | `t2gd-cli.exe` | match |
| linux-znver4 | not run, no AVX-512 on the packaging host | see Known limitations |
| macos-arm64 | not re-run on the packaging host | carried from the build host |

The Linux and Windows lines were run on the packaging host. The macOS value is
carried from its own build host, because the packaging host is Linux and the
macOS binaries were not rebuilt for this release, only repacked, with the
executable hashes asserted unchanged across the repack.

BGZF block boundaries can differ between a T2GD `sort` and an external sort of
the same data while the record stream is identical. Use `t2gd checksum`, which
is order-agnostic and content-based, when you need to prove two BAMs hold the
same records irrespective of block layout.

## Build provenance

| Item | Linux | macOS arm64 | Windows x86_64 |
|---|---|---|---|
| Compiler | LDC 1.42.0 (DMD v2.112.1, LLVM 21.1.8) | LDC 1.42.0 (DMD v2.112.1, LLVM 21.1.8) | LDC 1.40.0 (DMD v2.110.0, LLVM 19.1.3) |
| Platform toolchain | GNU ld, glibc | Apple clang 21.0.0, macOS 26.2 | MSVC 19.50.35726 for x64 |
| Build type | `release-znver4`, `release-znver2`, `release-broadwell` | `release-apple` | `release` |
| GTK 3 | not linked, loaded at runtime | 3.24.52, loaded at runtime | mingw-w64-x86_64-gtk3 3.24.51-2, bundled |

Common to all three: dub 1.41.0, dependency versions pinned by
`dub.selections.json` which travels inside the build kit, gtk-d 3.10.0 loaded
at runtime, and a test gate of 66 modules passing unit tests.

Windows used LDC 1.40.0 rather than the 1.42.0 used on the other two platforms.
That is a real deviation from the build kit and is recorded rather than
smoothed over. It has no observed effect on output: the Windows binary
reproduces the reference record stream checksum exactly, which is the property
the release is gated on.

The MSYS2 snapshot the 47 bundled DLLs came from is not recorded. It does not
affect the artifact you download, which is verified by hash, by import table
and by the record stream gate like every other build.

The binaries are not code-signed. On macOS, clear the quarantine attribute
after unpacking with `xattr -dr com.apple.quarantine <folder>`. On Windows,
SmartScreen will warn on first run; choose **More info** then **Run anyway**.
Both are consequences of an unsigned download, not of anything the binary does.

## Known limitations

* The znver4 build was not executed before release. The machine that packaged
  it has no AVX-512, so `./t2gd-cli --version` from that build exits 132, which
  is SIGILL. That is positive evidence the build really targeted znver4 and it
  is not evidence that it converts correctly. The znver2 and broadwell builds
  were both run against the reference record stream and both matched. If you
  have an AVX-512 machine, run `t2gd checksum` against a broadwell result once
  before trusting znver4 on real work.
* The manual built into the executable carries a screenshot of every tab, and
  two of those pictures are stale in this build. The Help tab picture predates
  the last five topics, so it shows a nine topic navigator where the manual
  actually carries fourteen. The About tab picture still reads v1.18.0
  "Fafnir". Both are pictures only: the manual text, the live navigator and the
  real About tab are all correct, and the copies of both figures in this
  repository under `figures/` were recaptured against 1.19.0. The manual is
  compiled into the binary, so correcting the embedded copies means rebuilding
  all five platforms.
* The 1.18.0 section of [CHANGELOG.md](CHANGELOG.md) opens "The first public
  release". That was written before the decision not to distribute Fafnir, and
  it is wrong: 1.19.0 is the first release to leave the building. The changelog
  ships inside all five archives, so correcting the line would mean repacking a
  signed macOS bundle and a Windows payload for one sentence. It is corrected
  here instead.
* There is no Intel Mac build and no universal binary.
* Below roughly 4 GB of memory, a human sized annotation will not fit however
  the run is configured.

## Licence

The binaries, the bundled documentation and the Python reference implementation
under [python/](python/) are all licensed under [CC BY-NC-ND 4.0](LICENSE). The
NoDerivatives term applies to the Python source too: it is published to be read,
run and cited, not forked. The T2GD D source tree is not covered by this licence
and is not distributed here. For commercial licensing, see https://biocodecs.org.

Note that `python/` is in the repository, not in these archives. The five
release archives contain the binary and its documentation only.

Copyright (c) 2026 Biocodecs, Arnaroo Ribologicals, COMPASS.
