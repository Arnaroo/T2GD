# T2GD changelog

Release notes for T2GD, the transcriptome-space to genome-space BAM
conversion toolkit. This file records changes that affect the command line
surface, the BAM output, or the install instructions.

## 1.19.0 "Shenlong" (2026-07-31)

Packaging and performance. There is no change to the command line surface and
no change to any record T2GD writes. If you are scripting against 1.18.0,
nothing here requires you to change anything, with one exception on Windows,
noted below, where the command line moves to a second executable.

### The graphical interface no longer opens a terminal beside itself

Launching the GUI in the ordinary way used to produce a second, empty window:
a black console on Windows, a Terminal window on macOS. Both are gone. The two
causes are unrelated, so the two fixes are different.

**Windows now ships two executables**, `t2gd.exe` for the interface and
`t2gd-cli.exe` for the command line. A Windows program declares at link time
whether it owns a console and cannot answer both ways. The single `t2gd.exe`
of 1.18.0 answered "yes", which is where the empty window came from; it now
answers "no". The flag is verified in the PE header, and launching `t2gd.exe`
on a live Windows desktop was observed to open the interface with no console
window beside it.

The consequence is worth knowing rather than rediscovering: a program without a
console has nowhere to print, so `t2gd.exe --cli --version` produces no output
when you run it in a terminal. That is the design, not a fault. Redirection is
unaffected, because a redirected handle is inherited from the shell rather than
allocated by the program, so `t2gd.exe --cli --version > out.txt` does write
the file. **Use `t2gd-cli.exe` for all command line work** and the question
does not arise.

**macOS now ships `T2GD.app`.** Finder does not launch a bare executable
directly. It hands it to Terminal, which opens a window and runs the program
inside it. Drag the bundle to `/Applications` and open it from there; it
launches on its own. The bare `t2gd` is still in the archive for anyone who
wants it from a shell.

The bundle finds the GTK 3 runtime by itself in `/opt/homebrew/lib` or
`/usr/local/lib` and says so in a dialog if it is missing. It has to: an app
launched from Finder inherits the launchd environment rather than your shell's,
so a `DYLD_LIBRARY_PATH` set in your profile never reaches it, and with no
terminal attached a loader error would go nowhere you could see it. Running the
bare `t2gd` from a shell is still the case where you set the variable yourself.

### The built-in manual matches the packaging again

The *Installing T2GD* topic inside the binary had drifted. It described a
`t2gd-cli-static` binary and a `generic` build variant, neither of which has
ever been in a release; it claimed a macOS `x86_64` build that does not exist;
and its unpack example named a directory the archives do not produce. It has
been rewritten from the artifacts and now agrees with `INSTALL.md`.

It also implied that GTK 3 was needed only to install the full binary, because
GTK does not appear in `readelf -d` NEEDED. That was wrong, and in a way that
would waste your time on a compute node: GTK is absent from that list because
it is resolved with `dlopen` rather than linked, not because it is optional.
`t2gd` loads GTK during start-up, before it looks at your arguments, so on a
machine without GTK it fails even for `t2gd --cli --version`. `t2gd-cli` is the
binary that contains no graphical code and needs none. The corrected text says
so plainly.

### Faster `depth`, faster BAM writing

These changes were developed under the number 1.18.1, which was never
released; the binaries built under it existed only for measurement. They ship
here.

* **`depth` and `coverage` are about 3× faster.** They no longer thrash the
  garbage collector on the per-reference column window, and the integer
  formatter no longer performs a 64-bit hardware divide per digit. On a 175 MB
  nanopore BAM emitting 316 M positions, `depth -t 1` goes from 51.8 s to
  17.7 s. The larger change is in work rather than wall clock: at `-t 8` the
  old build spent 215 CPU-seconds to buy 14 % of wall time over `-t 1`, and now
  spends 33. Output is byte-for-byte identical to 1.18.0, verified across 12
  fixtures × `{default, -a, -aa}` × `{-t 1, 4, 8}`.
* **BAM writing is about 1.9× faster.** BGZF compression now uses libdeflate
  instead of zlib, which affects every subcommand that writes a BAM. `sort -t 8
  --bgzf-threads 8 --read-threads 8` on a 175 MB BAM goes from 4.85 s to
  2.42 s. libdeflate is statically linked; the shared library list is unchanged.
* **The compressed bytes differ from 1.18.0 but the records do not.**
  libdeflate and zlib both emit valid DEFLATE and make different, equally legal
  choices. File size shifts by about a percent, and **the direction depends on
  the data**: −1.2 % on one sort output, but +1.1 % on the demo conversion.
  Budget for a percent either way rather than for a saving. If you have pinned
  a checksum of a **BAM file** it will change; a checksum of `samtools view`
  output will not. Use `t2gd checksum`, which is content-based and
  order-agnostic, if you need to prove two BAMs hold the same records.

### Known limitations

* The znver4 build was not executed before release. The host that packaged it
  has no AVX-512, so the binary exits 132 there, which is SIGILL. That confirms
  the build really targeted znver4 and says nothing about whether it converts
  correctly. The znver2 and broadwell builds were both run against the
  reference record stream and both matched.
* The screenshot of the Help tab in the built-in manual still predates the last
  five topics, so it shows a nine topic navigator rather than the fourteen
  topics actually present. The manual text is correct; only the picture of it
  is out of date.
* There is no Intel Mac build and no universal binary.
* Below roughly 4 GB of memory, a human sized annotation will not fit however
  the run is configured.

## 1.18.0 "Fafnir" (2026-07-30)

The first public release. T2GD converts alignments made against a
transcriptome FASTA into genome coordinates, using a GTF annotation as the
map, and ships 36 subcommands around that core operation. The paragraphs
below describe what is in this release rather than what changed from a
private version, since there is no earlier public version to compare
against.

### Conversion

`t2gd convert` lifts each transcript-space alignment onto the genome,
splitting the CIGAR at exon boundaries and inserting an `N` operation for
every intron the alignment crosses. Reads that cannot be placed are counted
and reported by reason rather than dropped silently.

* **Selective conversion.** `--gene-list FILE` restricts the run to reads on
  the transcripts of the listed genes, and `--tx-list FILE` restricts to the
  listed transcripts. Given together the two combine as a union. One
  identifier per line, blank lines and `#` comments ignored, version suffixes
  optional, and both `gene_id` and `gene_name` are matched. This is a
  convenience filter for targeted panels and demo data, not a speed feature;
  a whole-transcriptome run is already fast. Output is exactly what a
  post-hoc `filter` over a full conversion would produce.

* **Identifier resolution.** The commonest failure in this kind of
  conversion is a mismatch between the transcript names in the BAM and the
  names in the GTF, usually a version suffix present on one side only. The
  `auto` resolver probes the header and picks between strict matching and
  version stripping. `--strip-version` and `--id-resolver permissive` force
  the behaviour when the names differ in some other way. A run reports what
  it resolved, so a near-empty output is diagnosable in one line rather than
  by inspection.

* **Species presets.** `--species` sets the maximum implied intron length:
  human 500,000, mouse 240,000, drosophila 100,000, yeast 2,000.
  `--max-intron` sets it directly.

* **Memory control.** `--no-recover-secondary-tags` drops the cache of
  primary alignments that exists to restore `MM` and `ML` base modification
  tags onto secondary records, and `--disk-spill` writes each batch to a
  temporary BAM and merges at the end. Together they make resident memory
  track the in-flight window rather than the input size. Under a 16 GB cap,
  this recipe converts a 15 GB direct-RNA BAM of 44.9 million reads at
  4.3 GB peak resident memory.

* **Sizing.** `--profile auto` is the default and reads the input size, the
  core count and the available memory before choosing thread count, batch
  size, compression level and whether to spill. `balanced`, `lowmem`, `fast`
  and `maxcompress` are the explicit presets. Anything set explicitly wins
  over the preset.

* **Run logs you can keep.** `--log-file PATH` writes a full trace to a file
  independent of what the console shows, so a quiet terminal can still leave
  a complete record, and `--log-verbosity 0..3` sets the level of that file
  sink. The console keeps `-v`, `-vv` and `--quiet`.

* **Structured output.** A run prints a header naming it, a banner per phase
  with its own timing, and an end-of-run summary rendered as a table.
  Progress lines carry an ETA. `--explain` prints a legend under the summary
  saying what each row counts and what a healthy value looks like, covering
  the validation summary too when `--validate` is on.

### Splice junctions

`t2gd junctions` catalogues every intron in a genome-space BAM. It walks
the CIGAR `N` operations, aggregates identical introns into one row carrying
its read support, and writes a TSV of chrom, start, end, strand, strand_src,
support, intron_len, annotation and motif. Coordinates are 1-based inclusive
intron bounds, the convention GTF and STAR's `SJ.out.tab` use, so a row joins
directly against either.

* With `-g annot.gtf` each junction is classified against the annotated exon
  boundaries as annotated, novel combination (both ends known but not this
  pairing, that is, exon skipping), novel donor, novel acceptor, or fully
  novel.
* With `-r genome.fa` each is classified by splice motif: GT-AG, GC-AG,
  AT-AC or non-canonical. The reverse-complement forms are read off the plus
  strand, so the motif is named on the transcript strand.
* Strand comes from the best evidence available, in order: the splice motif
  (needs `-r`), minimap2's `ts:A` tag corrected to genomic orientation, then
  the alignment FLAG. The `strand_src` column records which one answered, so
  a FLAG-derived call is never mistaken for a motif-derived one. A run that
  falls back to FLAG with no reference supplied says so in the summary.
* `--plot DIR` writes three SVGs: splice-motif composition, annotation
  class, and the intron-length distribution.
* `--min-support S` drops thinly supported junctions, `--min-mapq Q` skips
  low-confidence alignments, and `--all-alignments` opts secondary and
  supplementary records in (primary only by default).
* The table goes to stdout, or to `-o`. The summary follows whichever stream
  the table left free, so `t2gd junctions in.bam > sj.tsv` gives a clean TSV
  plus a readable summary at the terminal.
* Motif and annotation sections are omitted from the summary entirely when
  the run had no reference or no GTF, rather than printed as a column of
  zeros a reader could mistake for a finding.

This answers whether a conversion landed on real introns. Neither `stats`,
which bins the `N` operation count per record, nor `validate`, which counts
records with two or more `N` operations, could say, because neither emits
coordinates.

### Graphical interface

The same executable is both a GTK 3 desktop application and a command line
tool. Run it with no arguments for the interface, or put `--cli` in front of
a subcommand to run headless.

* Twelve tabs: Convert, Inject Summary, Subset, Tools, Instruments, Count,
  Features, Stats, Plots, Log, Help and About. The first six run work, the
  next four show what happened, and the last two are documentation.
* Every operation except `checksum` has a graphical surface. `tagcheck` joins
  the inspect and report cluster on the Instruments tab, which completes the
  set.
* Every tab that runs something builds a command line and hands it to the same
  dispatcher the terminal uses, so anything you can do in the window has an
  exact textual equivalent.
* Figures on the **Features** tab gained zoom and reset controls, a scale
  selector, and **Save all to directory** and **Save tiled summary SVG**
  actions, matching the Plots tab. The Plots tab sets every panel at once from
  **All plots Y scale**, offering linear, log2, log10 and natural log, with a
  per-panel **Scale** selector for anything that should differ, and writes
  figures out with the same two save actions.
* The Log tab exposes the file sink and verbosity controls, so a quiet console
  with a detailed file is one selection away, and has **Clear log** and
  **Save log** buttons.
* URLs in the About and Help tabs are clickable.
* Development scaffolding text has been removed from the Instruments tab and
  from other operator-facing labels.

### Built-in manual

T2GD ships its manual inside the executable. Nothing is fetched and nothing
is installed alongside, so `t2gd help <topic>` and the Help tab work on a
machine with no network, no data directory and nothing on the path.

* Fourteen topics, about 13,500 words: what the tool is, how to install it,
  a quick start, the conversion algorithm, a guided tour of all twelve
  tabs, all 36 subcommands, worked scenarios, run variants from laptop to
  cluster, performance and resources, how to read the run summary, the
  per-read SAM tag namespace, exit codes, troubleshooting, and the licence.
* Twenty figures, including a screenshot of every tab, two schematics of the
  conversion and the pipeline, and three performance charts.
* The Help tab is a formatted document reader with headings, tables, code
  blocks, lists, quotes and figures. Links between topics jump to the right
  section, links to a command open its help, and links to a web address open
  your browser. Ctrl+F searches inside a page, with match counts and
  Return and Shift+Return to step through.
* A generated command reference heads the navigator, listing all 36
  subcommands grouped as in the command line usage, with a details link on
  every row. It is built from the command registry, so it cannot fall out of
  step with the tool.
* Command help bodies are shown verbatim in the interface, byte for byte
  what `t2gd <command> --help` prints, from the same source. The terminal
  and the interface cannot disagree about what a topic says.

### Command line consistency

* **The annotation flag is spelled the same way everywhere.** `filter` gains
  `-g` as the short form of `--gtf`, matching `convert`, `validate` and
  `junctions`. `count` gains `--gtf` as a synonym for `-a/--annotation`, so
  `--gtf PATH` works on all five commands that read a GTF. Nothing was
  renamed and nothing was removed. In particular `count -g` still means
  `--attribute`, the grouping key, because `count` follows featureCounts,
  where `-a` is the annotation and `-g` is the attribute; reusing `-g` for
  the file path there would have silently reinterpreted an existing
  `count -g gene_id` as a filename. Both aliases are verified against real
  data rather than against the help text: `count -a` and `count --gtf`
  produce byte-identical tables of 78,895 rows on GRCh38.114, and
  `filter --gtf` and `filter -g` select the same 5,616 reads on TP53.

* **`@PG` provenance is uniform.** Every BAM-writing subcommand stamps
  `VN:<version>-<codename>`, for example `VN:1.18.0-Fafnir`. Both
  pair-restorer paths, in memory and streaming, are included.

* **The `--help` subcommand listing is generated from the command registry**
  rather than maintained by hand, so it cannot drift from the tool.

### Platforms

Every platform produces the same records from the same input, byte for byte,
so a result does not change when you move machines.

| Platform | Binaries | Requirement |
|---|---|---|
| Linux x86_64 znver4 | `t2gd`, `t2gd-cli` | AVX-512, so AMD Zen 4 or newer |
| Linux x86_64 znver2 | `t2gd`, `t2gd-cli` | AMD Zen 2 or newer |
| Linux x86_64 broadwell | `t2gd`, `t2gd-cli` | widest x86_64 reach |
| macOS arm64 | `t2gd`, `t2gd-cli` | Apple Silicon M1 or newer, macOS 14+ |
| Windows x86_64 | `t2gd.exe` | any x86-64, Windows 10 or newer |

`t2gd` is the full build and runs headless as `t2gd --cli <subcommand>`.
`t2gd-cli` contains no graphical code at all and is the binary to use on
HPC nodes and in containers.

All binaries are static beyond the platform system libraries. The D runtime
and libdeflate are linked in. On Linux, `readelf -d` NEEDED lists only libz,
libm, libgcc_s, libc and ld-linux. On macOS, `otool -L` lists only libz,
libSystem and libobjc, all from `/usr/lib`, with no Homebrew path baked in
and no `LC_RPATH`. On Windows the import table lists only `KERNEL32.dll`,
`ADVAPI32.dll` and `WS2_32.dll`.

GTK 3 is absent from the link record on every platform, including in the
full build, because the toolkit is loaded at startup rather than linked.
That is a runtime load, not a weak link, so the full binary still needs
GTK present at startup even when you run it as `t2gd --cli`. The binary
that needs no GTK at all is `t2gd-cli`, which contains no graphical code.

Two consequences worth knowing before you unpack:

* **On macOS, use `t2gd-cli` for command line work.** macOS has no system
  wide library search path that finds Homebrew, so unless you point the
  loader at GTK yourself the full binary exits at startup with
  `Library load failed (libatk-1.0.0.dylib)`, including when you run it as
  `t2gd --cli`. `t2gd-cli` needs none of this.

* **On Windows, keep the folder together.** The bundle ships the GTK 3
  runtime beside `t2gd.exe`, along with the gdk-pixbuf loaders under `lib\`
  and the themes and icons under `share\`. Windows searches the executable's
  own directory first, so nothing needs installing and no environment
  variable is required, but moving `t2gd.exe` out on its own breaks the
  graphical interface. Because the runtime travels with the bundle, Windows
  ships one executable where Linux and macOS ship two, and the command line
  path works out of the box.

### Known limitations

* The Windows graphical interface has not been verified on a live desktop
  session. The GTK stack loads and every symbol resolves, but no interactive
  run was observed. The command line path is verified on Windows to the same
  standard as the other platforms.
* The built-in **Installing T2GD** manual topic predates the final release
  packaging and names archives and build variants that differ from what is
  actually shipped. Use `INSTALL.md` in this repository, which is written
  from the artifacts.
* The screenshot of the Help tab in the built-in manual was taken before the
  last five topics were written, so it shows a nine topic navigator rather
  than the fourteen topics actually present. The manual text is correct; only
  the picture of it is out of date.
* There is no Intel Mac build and no universal binary.
* Below roughly 4 GB of memory, a human sized annotation will not fit
  however the run is configured.
