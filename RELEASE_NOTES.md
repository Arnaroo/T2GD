# T2GD 1.19.1 "Shenlong"

A build-recipe release. It is built from the same source tree as 1.19.0
"Shenlong" (2026-07-31) and produces the same records; what changed is how the
binaries are compiled. The codename does not advance, deliberately, because a
new codename would imply new software.

T2GD converts alignments made against a transcriptome FASTA into genome
coordinates, using a GTF annotation as the map, and ships 36 subcommands around
that core operation. See [CHANGELOG.md](CHANGELOG.md) for what is in the
release and [INSTALL.md](INSTALL.md) for how to install it.

**If you are running 1.19.0, nothing here requires you to change anything.**
There is no source change, no change to the command line surface, and no change
to any record T2GD writes. Upgrade if you want the speed.

## What is new in 1.19.1

Link time optimisation (`--flto=full`) is removed from the five shipping
release recipes: `release-znver4`, `release-znver2`, `release-broadwell`,
`release-apple` and `release-generic`. That is the whole change.

LTO had been carried since 1.15.x on the assumption that it helps. It was
measured instead, and it does not help — it costs. The measurement was made on
a 96-CPU dual EPYC 9474F node under exclusive, quiescence-gated allocation, on
a 4.7 GB long-read BAM, with nine replicates per cell. Medians below; negative
means the binary **without** LTO is faster.

| op | threads | with LTO | without LTO | change |
|---|---|---|---|---|
| `depth` | 1 | 162.78 s | 78.57 s | -51.73% |
| `flagstat` | 8 | 14.75 s | 11.92 s | -19.19% |
| `view_count` | 8 | 12.59 s | 10.89 s | -13.50% |
| `flagstat` | 1 | 39.30 s | 35.18 s | -10.48% |
| `convert` | 8 | 68.18 s | 61.76 s | -9.42% |
| `view_count` | 1 | 36.20 s | 32.84 s | -9.26% |
| `convert` | 1 | 169.88 s | 154.20 s | -9.23% |
| `filter` | 8 | 51.42 s | 46.91 s | -8.77% |
| `sort` | 8 | 101.43 s | 95.78 s | -5.57% |
| `depth` | 8 | 29.85 s | 28.57 s | -4.29% |
| `sort` | 1 | 445.26 s | 443.06 s | -0.49% |
| `filter` | 1 | 231.61 s | 233.27 s | +0.72% |

Not one cell is meaningfully faster with LTO. The single positive number is
inside the run-to-run spread. Four further cells are excluded from the table
because the two builds did not run at comparable thread width, which would make
a wall-clock comparison between them a comparison of something other than the
code.

`depth` at one thread is the headline and also the least surprising result.
`depth.d` carries a hand-written multiply-shift division workaround at lines
1040 and 1344 that exists solely because LTO miscompiled the straightforward
form. Removing LTO removes the reason for that workaround; the workaround is
left in place for now, because it is correct either way and this release
changes no source.

**Correctness is gated, not assumed.** All 18 record-stream digest groups agreed
across every build tested, with zero mismatches, on both x86-64 and Apple
Silicon. Removing LTO changes no output. The per-release gate is reported under
**Determinism across platforms** below.

**Windows is unaffected, and it is worth knowing why.** Windows has never been
an LTO build: `release` is not defined in `dub.json`, so `dub build -b release`
falls back to dub's own built-in recipe of `-release -O -inline`. The five build
types this release edits are the Linux and macOS ones. The Windows executables
therefore differ from 1.19.0 only in the version strings compiled into them.

### What you may notice

* The `@PG` `VN:` field moves from `1.19.0-Shenlong` to `1.19.1-Shenlong`. This
  is the only difference in a BAM header, and it does not affect records. Two
  BAMs converted by 1.19.0 and 1.19.1 will not be byte-identical for that reason
  alone; their record streams are.
* Binary size moves, and not in the same direction on both platforms.

| Binary | 1.19.0 | 1.19.1 | Change |
|---|---:|---:|---:|
| `linux-broadwell/t2gd` | 12,372,728 | 9,927,464 | -19.8% |
| `linux-broadwell/t2gd-cli` | 5,495,096 | 3,778,888 | -31.2% |
| `macos-arm64/t2gd` | 7,252,432 | 13,208,960 | +82.1% |
| `macos-arm64/t2gd-cli` | 3,445,248 | 4,491,744 | +30.4% |

The other two Linux marches move by the same proportions: `t2gd` -20.4% on
znver4 and -19.4% on znver2, `t2gd-cli` -32.4% and -30.7%.

That divergence is mostly the strip step rather than the code. Linux strips with
`--strip-all` and discards the symbol table outright. macOS has to use
`strip -x` and keep the global symbols, because stripping them invalidates the
ad-hoc signature and on Apple Silicon an invalid signature is fatal. Without LTO
far fewer symbols have been internalised, so far more of them survive `strip -x`
— the strip removed 438 KB at 1.19.1 against 2.06 MB at 1.19.0. Unstripped, the
two platforms agree to within half a percent, at 13.64 MB on Linux broadwell
against 13.65 MB on macOS for the graphical build. Size is not the objective
here and no timing conclusion follows from it in either direction.

## Artifacts

| Platform | Archive | Size | Binaries |
|---|---|---:|---|
| Linux x86_64, znver4 | `t2gd-1.19.1-Shenlong-linux-x86_64-znver4.tar.gz` | 4,290,601 | `t2gd`, `t2gd-cli` |
| Linux x86_64, znver2 | `t2gd-1.19.1-Shenlong-linux-x86_64-znver2.tar.gz` | 4,237,374 | `t2gd`, `t2gd-cli` |
| Linux x86_64, broadwell | `t2gd-1.19.1-Shenlong-linux-x86_64-broadwell.tar.gz` | 4,248,488 | `t2gd`, `t2gd-cli` |
| macOS arm64 | `t2gd-1.19.1-Shenlong-macos-arm64.tar.gz` | 8,559,092 | `T2GD.app`, `t2gd`, `t2gd-cli` |
| Windows x86_64 | `t2gd-1.19.1-Shenlong-windows-x86_64.zip` | 27,172,265 | `t2gd.exe`, `t2gd-cli.exe` |
| Windows x86_64, installer | `t2gd-1.19.1-Shenlong-windows-x86_64-setup.exe` | 19,599,036 | `t2gd.exe`, `t2gd-cli.exe` |

Sizes are bytes. The Linux archives are about 24 % smaller than the 1.19.0 ones
and the macOS archive about 39 % larger, for the stripping reason given above.

The Windows installer carries the same tree as the zip and is offered only as a
convenience: it puts the program under `Program Files`, adds Start-menu and
optional desktop shortcuts, and can put the install directory on `PATH`. It is
smaller than the zip because it uses solid LZMA2 rather than per-entry deflate,
not because it holds less. The one file it does not install is `SHA256SUMS`,
which certifies the zip and has no meaning once the tree has been installed.
Everything else matches byte for byte: 916 files, verified by comparing every
shared path between an installed tree and the unpacked zip.

**Which one.** If you are unsure, take `broadwell`; it runs everywhere the
other two Linux builds do. `znver4` needs AVX-512, so AMD Zen 4 or newer.
`znver2` needs AMD Zen 2 or newer. The macOS build is Apple Silicon only and
needs macOS 14 or newer. The Windows build runs on any x86-64 machine with
Windows 10 or newer.

**Which binary.** `t2gd` is the full build and runs headless as
`t2gd --cli <subcommand>`. `t2gd-cli` contains no graphical code at all and is
the binary to use on HPC nodes and in containers. On macOS, use `t2gd-cli` for
command line work: the full binary looks for GTK at startup and macOS has no
system-wide search path that finds a Homebrew install.

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
e823155f9823501577d93da1085576cc935e6d7c66557ea81f3b981a8288e0ec  t2gd-1.19.1-Shenlong-linux-x86_64-znver4.tar.gz
c8b0728ae50c584b1bc1c196207c925d985f4d20b0ca2a8feb0b33aaec9a0744  t2gd-1.19.1-Shenlong-linux-x86_64-znver2.tar.gz
cb0a5dd8ae7dd5fcbd780e93da887eff325a67fb32b18ab7f43a37644e34c318  t2gd-1.19.1-Shenlong-linux-x86_64-broadwell.tar.gz
e6b97dc27102353bea3509a951a6a85ecb094da2f415511a5a698b4902ae5499  t2gd-1.19.1-Shenlong-macos-arm64.tar.gz
ed940aa2f6d6dfc5f2c7497e55188a2c810fbd1784c860c8876d37141f064b71  t2gd-1.19.1-Shenlong-windows-x86_64.zip
671d6b5489819a8d1e45e6f81512863426032312c0b9ff7f2130cb9973860c58  t2gd-1.19.1-Shenlong-windows-x86_64-setup.exe
```

Verify a download:

```sh
sha256sum -c SHA256SUMS --ignore-missing
```

On macOS, `shasum -a 256 -c SHA256SUMS --ignore-missing`. On Windows,
`certutil -hashfile t2gd-1.19.1-Shenlong-windows-x86_64.zip SHA256`.

SHA-256 of the executables themselves, after unpacking. Each archive also
carries its own `SHA256SUMS`, which you can check from inside the unpacked
folder.

```
a1a5a6318f76ce382faf95c2d5c192d736c00e9877d0d7230ab33ba222010c06  linux-znver4/t2gd
7cb22fc9d60b9dba26a2f0f9b25c84b6958b38e45a467e9da5dcd460eb296218  linux-znver4/t2gd-cli
9e3ece76a7babfbfc3bd263ae153b73a06bda21cd6969d2f54e9a1bb0343188b  linux-znver2/t2gd
951d37452987dbc7d726db48178adf152c5679c62d5f1df8f2b10741bb0d9b2d  linux-znver2/t2gd-cli
f2283770d19b8f5d9a55eedfa4ff093408234ce108fe09e5f52f36cce007c7ed  linux-broadwell/t2gd
5f50fe5820f4842414d573efd25704368cb32cdef1ee5f000c9f3c1820aa0a22  linux-broadwell/t2gd-cli
0f169318f00068c800e975d1b5ef78715880ca7946edea9acafc9fa90c11ade6  macos-arm64/t2gd
af8ed5651b504641cdf93df6f7d62788eb053acebd10a17887d86514936badf7  macos-arm64/t2gd-cli
9c70c063740e38af9fdd612f8469c6289c51fa11e170ce9ca515d53e8dacfaa3  macos-arm64/T2GD.app/Contents/MacOS/T2GD
5a47b56f73e0915d59adfc1388e3ebc67b88ec01904e957279d62963a7e63750  macos-arm64/T2GD.app/Contents/MacOS/t2gd-bin
f86dcab12fc41c0b3b3263eee28f949551ad8e821973c63c8304b474861faaeb  windows-x64/t2gd.exe
3d473667b47d41a89cfa6ed0a3debb853eacf978ab14e90a4fddaa388eff5a74  windows-x64/t2gd-cli.exe
```

Two of those lines deserve a note. `T2GD.app/Contents/MacOS/t2gd-bin` is the
same build as the bare `macos-arm64/t2gd` but does not hash the same and is 16
bytes larger, because ad-hoc signing the bundle rewrote the signature blob
inside it. `T2GD.app/Contents/MacOS/T2GD` is not a build at all; it is the
small launcher script that finds the GTK runtime and then execs `t2gd-bin`, and
it is unchanged from 1.19.0, which is why its hash is the same in both releases.

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
not cover the bundled GTK runtime, which is 910 further files; those are
covered by the checksum of the archive as a whole.

The Windows archive additionally carries that runtime: 47 DLLs beside
`t2gd.exe`, the gdk-pixbuf loaders under `lib\` (17 files), and themes and
icons under `share\` (846 files), 917 files in the archive altogether. Nothing
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
linked in. Removing LTO does not change this; the link record is identical to
1.19.0 on every platform.

On Linux, `readelf -d` NEEDED lists only `libz`, `libm`, `libgcc_s`, `libc` and
`ld-linux` — verified on all six Linux binaries in this release. On macOS,
`otool -L` lists only `libz`, `libSystem` and `libobjc`, all from `/usr/lib`,
with no Homebrew path baked in and no `LC_RPATH`. On Windows the import table
lists only `KERNEL32.dll`, `ADVAPI32.dll` and `WS2_32.dll`.

GTK 3 is absent from the link record on every platform, including in the full
build, because the toolkit is loaded at startup rather than linked. That is a
runtime load, not a weak link, so the full binary still needs GTK present at
startup even when you run it as `t2gd --cli`. The binary that needs no GTK at
all is `t2gd-cli`, which contains no graphical code.

## Determinism across platforms

Every platform produces the same records from the same input. This is verified
on each release by comparing the record stream checksum of the same conversion
run on each build. A result therefore does not change when you move machines.

Because 1.19.1 changes no conversion code, the record stream it produces must
match 1.19.0 and 1.18.0 exactly. That is checked rather than assumed:

| Reference conversion | Records | 1.18.0 | 1.19.0 | 1.19.1 |
|---|---:|---|---|---|
| Demo (`tests/demo`, GRCh38 subset) | 59,886 | `34d6da6cd0356bd924d7381a3b4b2d23` | same | same |
| Internal short-read corpus, GRCh38.114 | 5,781,316 | `0fa6ed91f920987b02b4421c40e183e8` | same | not re-run |

The demo gate matches. The corpus gate was not re-run for this release; see
Known limitations. Note that the *files* are not identical and are not meant to
be: the `@PG` header line records the invoking command and the version that ran
it, so a header comparison would differ by design. The gate is on records only.

What was run against the demo value for this release, exactly:

| Build | Binary | Result |
|---|---|---|
| linux-znver2 | `t2gd-cli`, and `t2gd --cli` | match |
| linux-broadwell | `t2gd-cli`, and `t2gd --cli` | match |
| linux-znver4 | not run, no AVX-512 on the packaging host | see Known limitations |
| macos-arm64 | run on the build host, 18 digest groups | match |
| windows-x64 | `t2gd-cli.exe`, `t2gd.exe --cli`, under wine | match, see the note below the table |

The Linux lines were run on the packaging host, both directly and through
`t2gd --cli` on the graphical build, giving 59,886 records and the reference
md5 in every case. The macOS value comes from its own build host, where the
full 18-group digest comparison was run against the LTO build before the host
was wiped; the archive shipped here was repacked from that stage with the
executable hashes asserted unchanged across the repack.

**The Windows line needs its qualification stated plainly, because the word
"match" on its own would claim more than was done.** The Windows binaries were
not run on Windows by the packaging side. They were run on the packaging host
under wine 11.15, in three configurations — `t2gd-cli.exe` at `-t 8` and at
`-t 1`, and `t2gd.exe --cli` at `-t 8` — and all three produced 59,886 records
and the reference md5.

What that does and does not establish is worth separating. Wine is not an
emulator: the x86-64 machine code in `t2gd-cli.exe` executes natively on this
CPU, so everything the gate is actually aimed at — the compiler's codegen, the
conversion arithmetic, the CIGAR and intron handling, the BGZF writer — is
genuinely exercised, and a codegen defect would have shown up here. What wine
substitutes is the Win32 API beneath it. So this result does not cover
Microsoft's own implementation of file I/O, threading or the C runtime, and it
is not a substitute for running the binary on Windows. The build operator's own
run on the build machine is the native evidence; this is a second, independent
check made on a different host from a different starting point, and it agrees.

One incidental confirmation came out of it. The `-t 8` and `-t 1` outputs differ
by exactly one byte in the container while the record streams are bit-identical:
the thread count is recorded in the `@PG CL` line. That is the concrete case the
paragraph above describes, observed rather than asserted.

BGZF block boundaries can differ between a T2GD `sort` and an external sort of
the same data while the record stream is identical. Use `t2gd checksum`, which
is order-agnostic and content-based, when you need to prove two BAMs hold the
same records irrespective of block layout.

## Build provenance

| Item | Linux | macOS arm64 | Windows x86_64 |
|---|---|---|---|
| Compiler | LDC 1.42.0 (DMD v2.112.1, LLVM 21.1.8) | LDC 1.42.0 (DMD v2.112.1, LLVM 21.1.8) | LDC 1.40.0 (DMD v2.110.0, LLVM 19.1.3) |
| Platform toolchain | GNU ld, glibc | Apple clang 21.0.0, macOS 26.2 | MSVC 19.50.35726 x64 |
| Build type | `release-znver4`, `release-znver2`, `release-broadwell` | `release-apple` | `release` (dub built-in) |
| LTO | none | none | none, and never was |
| GTK 3 | not linked, loaded at runtime | 3.24.52, loaded at runtime | 3.24.51, bundled and loaded at runtime |

Common to all three: dub 1.41.0, dependency versions pinned by
`dub.selections.json` which travels inside the build kit, gtk-d 3.10.0 loaded
at runtime, and a test gate of 66 modules passing unit tests.

The `LTO` row is the point of this release. The Linux and macOS build types
previously read `--flto=full`; they now do not. Windows uses none of those five
build types — `release` is not defined in `dub.json`, so dub supplies its own
`-release -O -inline` — which is why the Windows column reads "never was".

The `Compiler` row is not uniform and should not be read as though it were. The
Windows build is LDC 1.40.0 where Linux and macOS are 1.42.0, and it carries the
older frontend and the older LLVM with it. This is the same divergence 1.19.0
had, for the same reason: it is the toolchain installed on the machine that does
the Windows builds. It is recorded rather than smoothed over because it is the
one place the five archives do not share a compiler.

Unlike 1.19.0, the Windows column here was read off the artifacts rather than
supplied by the operator. `ldc2-1.40.0-windows-multilib` survives as a path
string in both executables; the PE optional header gives linker 14.50, and the
Rich header's linker record gives build 35726, which is `MSVC 19.50.35726`. The
Rich header is identical tool-for-tool to 1.19.0's, so the build environment is
demonstrably unchanged between the two releases.

One consequence of that fallback is recorded as defect W2 and is unchanged
here: dub's built-in `release` sets `-release` but not `-boundscheck=off`, so
the Windows binary keeps bounds checking in `@safe` code that the Linux and
macOS builds drop. It is a slightly different program under a memory-safety
fault, and a confound in any cross-platform timing comparison. It is not
something to change inside a release whose entire purpose is a single
controlled build-flag change.

The MSYS2 snapshot the 47 bundled DLLs came from is not recorded. It does not
affect the artifact you download, which is verified by hash, by import table
and by the record stream gate like every other build.

It is worth being exact about one thing the wording above could otherwise
obscure. The bundled runtime is **not** byte-identical to 1.19.0's. The 47
top-level DLLs are the same count and GTK is the same 3.24.51, but `lib\` grew
from 15 files to 17 and `share\` from 834 to 846, so the MSYS2 snapshot this
build drew from is a later one. That is a change to what travels alongside the
program, not to the program, and it is the one respect in which "the same tree,
rebuilt without LTO" does not fully describe the Windows artifact. It has no
bearing on the LTO comparison, since Windows was never LTO'd and the runtime is
not compiled here at all.

The binaries are not code-signed. On macOS, clear the quarantine attribute
after unpacking with `xattr -dr com.apple.quarantine <folder>`. On Windows,
SmartScreen will warn on first run; choose **More info** then **Run anyway**.
Both are consequences of an unsigned download, not of anything the binary does.

The Windows installer is unsigned for the same reason, and it will draw a
louder SmartScreen warning than the zip does, because it asks for elevation and
offers to edit `PATH`. That combination is exactly the shape SmartScreen is
built to object to. If that is not a trade you want to make, use the zip: it
contains the same files and needs no elevation at all.

## Known limitations

* The znver4 build was not executed before release. The machine that packaged
  it has no AVX-512, so `./t2gd-cli --version` from that build exits 132, which
  is SIGILL. That is positive evidence the build really targeted znver4 and it
  is not evidence that it converts correctly. The znver2 and broadwell builds
  were both run against the reference record stream and both matched. If you
  have an AVX-512 machine, run `t2gd checksum` against a broadwell result once
  before trusting znver4 on real work.
* The 5.78 M-record internal corpus gate was not re-run for 1.19.1. The demo
  gate was, on four build/binary combinations, and the 18-group digest
  comparison behind the LTO decision covers far more ground than either. The
  corpus gate is a belt-and-braces check on a release that changes no source,
  and it is recorded as skipped rather than quietly dropped.
* The *Installing T2GD* topic built into the executable still gives its example
  filenames as `t2gd-1.19.0-...`. The instructions are correct; only the example
  version string is stale. The manual is compiled into the binary, so correcting
  it means rebuilding all five platforms, and the version number in an example
  unpack command is not worth that. The download page and
  [INSTALL.md](INSTALL.md) both carry the right names.
* The manual built into the executable carries a screenshot of every tab, and
  two of those pictures are stale, unchanged from 1.19.0. The Help tab picture
  shows a nine-topic navigator where the manual carries fourteen. The About tab
  picture still reads v1.18.0 "Fafnir". Both are pictures only: the manual text,
  the live navigator and the real About tab are all correct, and the copies of
  both figures in this repository under `figures/` are current.
* The 1.18.0 section of [CHANGELOG.md](CHANGELOG.md) opens "The first public
  release". That was written before the decision not to distribute Fafnir, and
  it is wrong: 1.19.0 was the first release to leave the building. The changelog
  ships inside all five archives and is installed by the Windows installer; the
  line is corrected here rather than by repacking a signed macOS bundle and a
  Windows payload for one sentence.
* There is no Intel Mac build and no universal binary.
* Below roughly 4 GB of memory, a human-sized annotation will not fit however
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
