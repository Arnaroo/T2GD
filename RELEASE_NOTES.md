# T2GD 1.22.0 "Vritra"

The release that goes with the revised T2G paper. `convert` changes three
defaults and writes its paired output sorted, as its header has always said;
the release also carries 1.20.0 to 1.21.3, five versions made while the paper
was under review and never published.

T2GD converts alignments made against a transcriptome FASTA into genome
coordinates, using a GTF annotation as the map, and ships 36 subcommands around
that core operation. See [CHANGELOG.md](CHANGELOG.md) for what is in the
release and [INSTALL.md](INSTALL.md) for how to install it.

**If you are running 1.19.1, read this first.** A default `convert` run now
writes one record where the aligner reported the same genomic alignment once
per isoform, recomputes `NH` for the reads that lost records, adds `XS:A` and
`ts:A` to every spliced record, and no longer drops a read for the size of an
annotated intron. To get the earlier record set back:

```sh
t2gd-cli convert ... --keep-isoform-duplicates --strand-tag none --max-intron 500000
```

On the demo input that gives the record stream of 1.19.1 byte for byte (the
checks are below). Paired output keeps its records but is now sorted.

## What is new in 1.22.0

* **Isoform duplicates are written once**, with `ta:Z` naming the isoforms a
  record stands for and `tn:i` counting them; `NH` is recomputed in genome
  space; `--unique-mapq N` and `--keep-isoform-duplicates` are new.
* **Strand tags on spliced records**: `XS:A` (HISAT2, STAR, TopHat) and `ts:A`
  (minimap2), which StringTie reads; `--strand-tag spliced|all|none`.
* **No intron limit by default** (`--max-intron 0`); the `--species` presets
  are one table with the Python reference.
* **The paired output is coordinate-sorted**, so `samtools index` takes it.
* **A fully static command line binary**, `t2gd-cli-static`, in every Linux
  archive, and a fourth Linux archive, `generic`, that carries it alone.
* From 1.20.0 to 1.21.3: `sort` reads SAM, `fastq -T` and `fasta -T` copy aux
  tags, `--no-pg` and `--pg-id`, an honest `@HD SO:` under `--no-sort`, the
  graphical binary hands every subcommand to the command line, and a BAM cut
  short (or still being written) is refused when it is opened instead of being
  read as complete.
* The **Python reference** under [python/](python/) is 5.8 and makes the same
  three `convert` changes.

### The binary behind the paper

`linux-generic/t2gd-cli-static` is, byte for byte, the build the revised
paper's measurements were made with (SHA-256 `f2546965cbb36e99...`). It was
rebuilt for this release from the frozen source with the same compiler and
recipe and came out identical, which is how this release knows its source is
the measured source. The direct RNA lifts of the paper were made with the build
before it, which differs only in the order of paired output.

### Threads

For one conversion at a time, `-t 8 --threads-bgzf 8` on eight cores reserved
for the job (a cluster allocation of that size, or `taskset` on a whole node)
was the fastest setting measured: restricted to as many cores as threads, every
input ran fastest on eight threads, and with `-t` alone on a whole 96-core node
the same lifts took up to 2.2 times as long. The default worker count, the
processors the process may use less two, is past that point on a large machine,
so give `-t`. [USAGE.md](USAGE.md) has the measurements.

## Artifacts

| Platform | Archive | Size | Binaries |
|---|---|---:|---|
| Linux x86_64, znver4 | `t2gd-1.22.0-Vritra-linux-x86_64-znver4.tar.gz` | 6,296,941 | `t2gd`, `t2gd-cli`, `t2gd-cli-static` |
| Linux x86_64, znver2 | `t2gd-1.22.0-Vritra-linux-x86_64-znver2.tar.gz` | 6,212,082 | `t2gd`, `t2gd-cli`, `t2gd-cli-static` |
| Linux x86_64, broadwell | `t2gd-1.22.0-Vritra-linux-x86_64-broadwell.tar.gz` | 6,230,025 | `t2gd`, `t2gd-cli`, `t2gd-cli-static` |
| Linux x86_64, generic (x86-64-v3) | `t2gd-1.22.0-Vritra-linux-x86_64-generic.tar.gz` | 1,888,948 | `t2gd-cli-static` |
| macOS arm64 | `t2gd-1.22.0-Vritra-macos-arm64.tar.gz` | 8,599,238 | `T2GD.app`, `t2gd`, `t2gd-cli` |
| Windows x86_64 | `t2gd-1.22.0-Vritra-windows-x86_64.zip` | 27,396,519 | `t2gd.exe`, `t2gd-cli.exe` |
| Windows x86_64, installer | `t2gd-1.22.0-Vritra-windows-x86_64-setup.exe` | 19,683,092 | `t2gd.exe`, `t2gd-cli.exe` |

Sizes are bytes. The Linux archives are larger than 1.19.1's because each now
carries the static binary as well.

**Which one.** If you are unsure, take `broadwell`; it runs everywhere the
other two microarchitecture builds do. `znver4` needs AVX-512, so AMD Zen 4 or
newer. `znver2` needs AMD Zen 2 or newer. `generic` needs AVX2 (Intel Haswell,
AMD Zen and newer) and carries only the static command line binary. The macOS
build is Apple Silicon only and needs macOS 14 or newer. The Windows build runs
on any x86-64 machine with Windows 10 or newer.

**Which binary.** `t2gd` is the full build and runs headless as
`t2gd --cli <subcommand>`. `t2gd-cli` contains no graphical code at all and is
the binary to use on HPC nodes and in containers. `t2gd-cli-static` is the same
command line program with no dynamic section, for minimal containers and hosts
whose C library is older or different. On macOS, use `t2gd-cli` for command
line work: the full binary looks for GTK at startup and macOS has no
system-wide search path that finds a Homebrew install. On Windows use
`t2gd-cli.exe` on the command line; keep the folder together, since moving
`t2gd.exe` out on its own breaks the graphical interface.

## Checksums

SHA-256 of the release archives. These are also in `SHA256SUMS` alongside the
archives.

```
28f3b787b730db52e48b2ccaca7f404f4548ca7caca9fdb544ab926615fa99a4  t2gd-1.22.0-Vritra-linux-x86_64-znver4.tar.gz
2c2cda266806fb40688f556d4f2f18f6b0cd85057a1c4bf2e7691e10ae2ac5b7  t2gd-1.22.0-Vritra-linux-x86_64-znver2.tar.gz
9b391a188cdc36aa79d0763160d265c9f22f7d1c70b6d7e95df88c08a8ab328e  t2gd-1.22.0-Vritra-linux-x86_64-broadwell.tar.gz
c3ecb886a2a039994c631cf20fa24a39e44c66370b1d5bf4225cd832018fa021  t2gd-1.22.0-Vritra-linux-x86_64-generic.tar.gz
8aa0cc319f2b9521d3cab85afef49b7b2ead152b8876d49379e503205032dcb8  t2gd-1.22.0-Vritra-macos-arm64.tar.gz
fa89080488f73f23086b10c7fddc26a5183b4ab05d5efebe94f56024f4aaf7cc  t2gd-1.22.0-Vritra-windows-x86_64.zip
157cd0c8d716f936e7619199c3a034dbc1961c079daabda6e228777aa1215762  t2gd-1.22.0-Vritra-windows-x86_64-setup.exe
```

Verify a download:

```sh
sha256sum -c SHA256SUMS --ignore-missing
```

On macOS, `shasum -a 256 -c SHA256SUMS --ignore-missing`. On Windows,
`certutil -hashfile t2gd-1.22.0-Vritra-windows-x86_64.zip SHA256`.

SHA-256 of the executables themselves, after unpacking. Each archive also
carries its own `SHA256SUMS`, which you can check from inside the unpacked
folder.

```
365676ba40d48f89acafec48df3dbd533119c83217ae8106f5b570773aedfca7  linux-znver4/t2gd
fa2426908997c01b9bdd9f3144143c62248b67514941cbf78578e00f346dc521  linux-znver4/t2gd-cli
152d29ce8c0bc067c047784b12eba48da96bf9400083995ae6539188a70c6dea  linux-znver4/t2gd-cli-static
6b132e72b0f5a6d754990c3b0562bbb797fa2a9e33f16a8e484dc3f328e03ef5  linux-znver2/t2gd
a79ac79042df394ad7a7756d3d72398bd44f531c1617712da70546ac237a2301  linux-znver2/t2gd-cli
7c97e425e8cbcaede76b3cf2cfaee6902d706519c19222ed59120ca88c93b545  linux-znver2/t2gd-cli-static
0820d87391beda8b48a148e41563d39e3193ae83f3701d143c801917462357f7  linux-broadwell/t2gd
0d9fb264e8a07ea971c66b029fe58bafbba5c2e18817473ea13ac3ecfd354131  linux-broadwell/t2gd-cli
89c985bb9de57cbea6a8331622189cc25047d40bfd2a366d3c8c893b92a978b4  linux-broadwell/t2gd-cli-static
f2546965cbb36e999f1ef38178acdbc88df5223b3aa12dd89f4e5cf44df885f5  linux-generic/t2gd-cli-static
2f5e5a0f158fc0b4f9e1d1844ca0bb7c4c75c078470888c5c0f3a0545c36842e  macos-arm64/t2gd
8f2b71b766ab4fb05b98ce162ecebaf3d400ae8f9a1f1fcd1f439c3511a2735e  macos-arm64/t2gd-cli
9c70c063740e38af9fdd612f8469c6289c51fa11e170ce9ca515d53e8dacfaa3  macos-arm64/T2GD.app/Contents/MacOS/T2GD
c36d0d2fccbe1e0715f3ca2efd8bb6df5f5b0a8fab5b1b8765c92d3d8c517a07  macos-arm64/T2GD.app/Contents/MacOS/t2gd-bin
3d7b572c3a6f8cc3fd9524bd4b24b9330ce9511212163bf710efe68501f666a9  windows-x64/t2gd.exe
6ef4bc959eac25c192faa49020961c61089c37a3f7b5e3b90f389656d30df591  windows-x64/t2gd-cli.exe
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

The Linux archives are reproducible: packing the same files again gives the
same bytes, because the member order is fixed, member times and owners are
clamped and the gzip header carries no time.

The Windows archive additionally carries the GTK 3 runtime beside `t2gd.exe`:
47 DLLs, the gdk-pixbuf loaders under `lib\`
(17 files) and themes and icons under `share\`
(846 files), 917 files in the folder
altogether. `SHA256SUMS` there covers the executables and the four
documents; the runtime is covered by the checksum of the archive as a whole.
`t2gd-cli.exe` needs none of it and runs on its own.

The macOS archive additionally carries `T2GD.app`. Open that rather than
double-clicking the bare `t2gd`: Finder hands a bare executable to Terminal,
so the bundle is what makes the interface open without one.

The manual is inside the executable. Nothing is fetched at runtime and nothing
is installed alongside, so `t2gd help` works on a machine with no network.

## Dependencies

None beyond the platform system libraries. The D runtime and libdeflate are
linked in.

On Linux, `readelf -d` NEEDED lists only `libz`, `libm`, `libgcc_s`, `libc` and
`ld-linux` for `t2gd` and `t2gd-cli`, verified on all six; the four
`t2gd-cli-static` binaries have no dynamic section at all, verified on all four.
The static binaries carry glibc 2.44 inside them. With it come a few functions
of the D standard library that look up user and network names and would need
the host's own glibc at run time; T2GD's code calls none of them, and the linker
names each one at build time. On macOS, `otool -L` lists only `/usr/lib/libz.1.dylib`, `/usr/lib/libSystem.B.dylib` and `/usr/lib/libobjc.A.dylib` for `t2gd` and `t2gd-cli`, with no Homebrew path. On
Windows the import table lists only `KERNEL32.dll`, `ADVAPI32.dll` and `WS2_32.dll` for `t2gd.exe` and `t2gd-cli.exe`.

GTK 3 is absent from the link record on every platform, including in the full
build, because the toolkit is loaded at startup rather than linked. That is a
runtime load, not a weak link, so the full binary still needs GTK present at
startup even when you run it as `t2gd --cli`. The binaries that need no GTK at
all are `t2gd-cli` and `t2gd-cli-static`, which contain no graphical code.

## Determinism across platforms

Every build produces the same records from the same input. This is checked on
each release by comparing the record stream checksum (`samtools view | md5sum`)
of the same conversion run on each build.

| Reference conversion | Records | Defaults of 1.22.0 | Duplicates kept, strand tags off |
|---|---:|---|---|
| Demo (`tests/demo`, GRCh38 subset), `-t 8` | 59,886 | `203a8410eaffe9cc119b70a191a278ba` | `34d6da6cd0356bd924d7381a3b4b2d23`, as 1.18.0 to 1.19.1 |
| Internal short-read corpus, GRCh38.114, also `--max-intron 500000` | 5,781,316 | not run | `0fa6ed91f920987b02b4421c40e183e8`, as 1.18.0 and 1.19.0 |

Under the defaults the demo output differs from the other column in exactly
its 49,903 spliced records, each of which gains `XS:A` and `ts:A`; the demo
reads have no isoform duplicates to collapse.

What was run for this release:

| Build | Binaries | Result |
|---|---|---|
| linux-generic | `t2gd-cli-static` | both demo digests match; the corpus matches; the Python reference agrees on every record |
| linux-znver2 | `t2gd-cli`, `t2gd --cli`, `t2gd-cli-static` | both demo digests match |
| linux-broadwell | `t2gd-cli`, `t2gd --cli`, `t2gd-cli-static` | both demo digests match |
| linux-znver4 | `t2gd-cli`, `t2gd --cli`, `t2gd-cli-static` | both demo digests match, on an AMD EPYC 9474F (Zen 4) machine; the packaging host has no AVX-512 |
| macos-arm64 | `t2gd-cli`, `t2gd --cli` | both demo digests match, on the build host (Apple M4, macOS 26.2) |
| windows-x64 | `t2gd-cli.exe`, `t2gd.exe --cli` | both demo digests match, under wine 11.19 on the packaging host |

The Linux runs were repeated on binaries unpacked from the archives above.

The Python reference 5.8 and `t2gd-cli-static` agree record for record on
`QNAME`, `FLAG`, `RNAME`, `POS`, `MAPQ`, `CIGAR` and every tag, on all 59,886
records of the demo input (`--no-pair-restore`) and on all four records of a
fixture that exercises the collapse (`--unique-mapq 60`).

BGZF block boundaries can differ between a T2GD `sort` and an external sort of
the same data while the record stream is identical. Use `t2gd checksum`, which
is order-agnostic and content-based, when you need to prove two BAMs hold the
same records irrespective of block layout or order.

## Build provenance

| Item | Linux | macOS arm64 | Windows x86_64 |
|---|---|---|---|
| Compiler | LDC 1.43.0 (DMD v2.113.0, LLVM 22.1.8) | LDC 1.43.0 (DMD v2.113.0, LLVM 22.1.8) | LDC 1.43.0 (DMD v2.113.0, LLVM 22.1.8) |
| Platform toolchain | GNU ld and strip (binutils 2.47), glibc 2.44 | Apple clang 21.0.0 and ld (Command Line Tools), macOS 26.2; `strip -x`, then an ad-hoc signature | MSVC 19.50 (Visual Studio Build Tools 18.4), Windows 11 26200; installer by Inno Setup 7.0.2 |
| Build type | `release-znver4`, `release-znver2`, `release-broadwell`; static: `release-<arm>-static`, `release-generic-static` | `release-apple` | `release` (dub built-in) |
| LTO | none | none | none |
| GTK 3 | not linked, loaded at runtime | not linked, loaded at runtime (Homebrew's GTK 3, which the bundle's launcher finds) | not linked, loaded at runtime from the bundled MSYS2 GTK 3.24.51 |

Common to all three: dependency versions pinned by `dub.selections.json`, which
travels inside the build kit; gtk-d 3.10.0 loaded at runtime; and a test gate of
68 modules passing unit tests (dub 1.42.0 on Linux).

## Known limitations

* The built-in **Installing T2GD** topic predates this release: it names three
  Linux builds and gives 1.19.0 file names. [INSTALL.md](INSTALL.md) and the
  `RUN_LINUX.txt` page in each archive are current. The manual is compiled in,
  and this release keeps the measured binary byte for byte.
* The screenshot of the Help tab in the built-in manual shows nine topics where
  the manual carries fourteen, and the About tab picture still reads v1.18.0.
  Both are pictures only.

## Citing this release

This release is archived on Zenodo with its binaries, so the snapshot holds
the programs as well as the repository:
[10.5281/zenodo.24433505](https://doi.org/10.5281/zenodo.24433505). The concept
DOI [10.5281/zenodo.21744718](https://doi.org/10.5281/zenodo.21744718) always
resolves to the latest version. [CITATION.cff](CITATION.cff) carries both.

## Licence

The binaries, the bundled documentation and the Python reference implementation
under [python/](python/) are all licensed under [CC BY-NC-ND 4.0](LICENSE). The
NoDerivatives term applies to the Python source too: it is published to be read,
run and cited, not forked. The T2GD D source tree is not covered by this licence
and is not distributed here. For commercial licensing, see https://biocodecs.org.

Note that `python/` is in the repository, not in these archives. The release
archives contain the binary and its documentation only.

Copyright (c) 2026 Biocodecs, Arnaroo Ribologicals, COMPASS.
