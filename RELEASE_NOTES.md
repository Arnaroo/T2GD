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
and the macOS archive about 39 % larger.

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
`ld-linux`, verified on all six Linux binaries in this release. On macOS,
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

What was run against the demo value for this release, exactly:

| Build | Binary | Result |
|---|---|---|
| linux-znver2 | `t2gd-cli`, and `t2gd --cli` | match |
| linux-broadwell | `t2gd-cli`, and `t2gd --cli` | match |
| linux-znver4 | `t2gd-cli`, and `t2gd --cli` | not run, no AVX-512 on the packaging host |
| macos-arm64 | run on the build host, 18 digest groups | match |
| windows-x64 | `t2gd-cli.exe`, `t2gd.exe --cli`, under wine | match |

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

## Licence

The binaries, the bundled documentation and the Python reference implementation
under [python/](python/) are all licensed under [CC BY-NC-ND 4.0](LICENSE). The
NoDerivatives term applies to the Python source too: it is published to be read,
run and cited, not forked. The T2GD D source tree is not covered by this licence
and is not distributed here. For commercial licensing, see https://biocodecs.org.

Note that `python/` is in the repository, not in these archives. The five
release archives contain the binary and its documentation only.

Copyright (c) 2026 Biocodecs, Arnaroo Ribologicals, COMPASS.
