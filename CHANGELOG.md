# T2GD changelog

Release notes for T2GD, the transcriptome-space to genome-space BAM
conversion toolkit. This file records changes that affect the command line
surface, the BAM output, or the install instructions.

## 1.22.0 "Vritra" (2026-11-01)

The release that goes with the revised T2G paper. `convert` changes three
defaults, and its paired output is now sorted as its header has always said.
It also carries 1.20.0 to 1.21.3, five versions made while the paper was under
review and never published; they are summarised at the end of this section.

**If you script against 1.19.1, read "Getting 1.19.1's records back" first.**
A default `convert` run now writes fewer records for reads that match several
isoforms, and adds two tags to every spliced record.

### Isoform duplicates are written once

An aligner working in transcript space reports a read once for every isoform
it matches. After the lift, many of those records are the same genomic
alignment: the same chromosome, position, strand and CIGAR, written several
times. `convert` now keeps one record for each, the primary when one of them is
primary. The record that stays carries `ta:Z`, the isoforms it stands for (its
own first), and `tn:i`, their number.

For every read that lost a record, `NH` is recomputed as the number of
non-supplementary records left in genome space, and when no primary survived (the aligner's primary was on
a transcript the annotation lacks) the first record left is promoted to primary.
`HI` is left as the aligner wrote it. MAPQ keeps the aligner's value, because
aligners use different scales (bowtie2 tops at 42, minimap2 at 60, STAR at
255); `--unique-mapq N` sets MAPQ N on a read whose placements collapsed to one.

The pass needs the sorted output, so `--no-sort` turns it off, with a warning.
`--keep-isoform-duplicates` keeps every record the aligner wrote. The run
summary gains rows counting what the pass did.

### Strand tags on spliced records

Every lifted record whose genome CIGAR has an `N` now carries `XS:A`, the
transcript's strand on the genome (the convention of HISAT2, STAR and TopHat),
and `ts:A`, the same strand relative to the record's own orientation
(minimap2's convention). StringTie reads both. Neither is written over a tag of
the same name that the aligner already wrote, such as bowtie2's `XS:i` (a
score) or Dorado's `ts:i` (trimmed samples). `--strand-tag all` extends them to
unspliced records; `--strand-tag none` turns them off.

### No intron limit by default

A read is no longer skipped because its alignment crosses a long annotated
intron. The intron comes from the annotation, so its size is not evidence
against the read. `--max-intron` now defaults to 0, no limit, and `--warn-intron`
still warns at 100,000. The `--species` presets are one table, shared with the
Python reference: human, mouse and zebrafish 500,000; plant 750,000; fly or
drosophila 100,000; worm 50,000; yeast 5,000. 1.19.1 had human 500,000, mouse
240,000, yeast 2,000 and drosophila 100,000. An explicit `--max-intron` wins
over a preset.

### The paired output is coordinate-sorted

Pair restoration wrote each pair when its second mate arrived, so every earlier
version wrote its paired output out of order under an `@HD SO:coordinate`
line, and `samtools index` refused it. The paired output is now sorted before
it is written, with the run's own thread and memory settings. `--no-sort` leaves
it unsorted, as before. Single-end output is unaffected.

### Getting 1.19.1's records back

```
t2gd-cli convert ... --keep-isoform-duplicates --strand-tag none --max-intron 500000
```

restores the earlier record set. On the demo input the record stream is then
byte-identical to 1.19.1's, and on a single-end corpus of 5.8 million records to
1.19.0's. Paired output holds the same records in a different order, because it
is now sorted; `t2gd checksum`, which ignores order, compares the records alone.

### Python reference 5.8

The reference implementation under `python/` makes the same three changes and
takes the same flags. On matched settings the two implementations agree record
for record: on all 59,886 records of the demo input, tags included, and on all
four records of a fixture built to exercise the collapse.

### Choosing a thread count

For one conversion at a time, give `-t 8 --threads-bgzf 8` on eight cores
reserved for the job, of one socket where possible: a cluster allocation of
that size enforces this, and on a whole node `taskset` does. Measured for the
paper on nodes of two 48-core AMD EPYC 9474F, restricted to as many cores as
threads, every input ran fastest on eight threads, 2.7 to 3.0 times faster
than on one, and no sixteen-thread run beat eight threads on one die. With
`-t` alone on a whole 96-core node the same lifts took up to 2.2 times as
long. The default worker count is the number of logical processors the
process may use, less two, which on a large node is far past that point, so
`-t` is worth giving explicitly.
This advice is in `USAGE.md`, not in the built-in help. The source of this
release is exactly the source the paper was measured with, and its generic
build is the measured binary byte for byte; changing the help text would have
changed it.

### A fully static Linux build

Each Linux archive now carries `t2gd-cli-static` beside `t2gd` and `t2gd-cli`:
the same command line program, linked with no dynamic section at all, so it
needs no C library on the host and runs in minimal containers and on systems
with an older or different C library. A fourth Linux archive, `generic`, holds
only `t2gd-cli-static`, built for x86-64-v3, which needs AVX2 (Intel Haswell,
AMD Zen and newer). It is byte for byte the build that made the revised
paper's timings; the paper's lifts were made with it, or with a build that
differs from it only in the order of paired output.

### Also in this release, from the unpublished 1.20.0 to 1.21.3

* **`sort` accepts SAM on `-i`**, encoding on the way in as `samtools sort`
  does. The product is byte-identical to encoding first and sorting second.
* **`fastq` and `fasta` copy aux tags with `-T TAG[,TAG...]`** (`'*'` for every
  tag) onto the read-name line, in the form `minimap2 -y` reads, byte-identical
  to `samtools fastq -T` on the probes tried. This is how base modification tags
  (`MM`, `ML`) survive a trip back through FASTQ.
* **`--no-pg` and `--pg-id ID`**, two global options: write no `@PG` line, or
  stamp one under a name of your choosing, so that two runs differing only in
  where their output went can produce identical bytes. `convert` and
  `inject-summary` no longer put the path of the t2gd binary into the `@PG`
  line.
* **`@HD SO:` tells the truth under `--no-sort`**: `convert --no-sort` now writes
  `SO:unsorted`. A length in `@SQ LN:` that was estimated because no
  `--chrom-sizes` was given is now reported in a warning.
* **The graphical binary hands every subcommand to the command line.** Before,
  `t2gd count`, `t2gd flagstat` and twenty-odd others opened a window instead
  of running, which to a script looks like a hang. `--list-commands` prints
  every subcommand, one per line.
* **A BAM that does not end with its 28-byte end-of-file block is refused when
  it is opened**, before any record is written anywhere. That includes a file
  MinKNOW or Dorado is still writing. An end-of-file block in the middle of a
  file is skipped, a block whose stated size disagrees with what it inflates to
  is refused, and a failed open no longer leaves threads running or hangs.
  Before, a cut BAM drew a warning and was read as though it were complete.
* **A BGZF block filled to the maximum the format allows now reads on one
  thread.** Such files (INDEGRA writes them) failed at `-t 1` and read at
  `-t 2`.
* **The tag table in the manual was corrected**: `gn` is the GTF `gene_id`, not
  `gene_name`; `xi` is a 0 or 1 flag; `im` is the largest intron in bp; `ro` is
  1 or -1; `es` and `ee` are 3' end distances; `gs` and `ge` are this
  alignment's own lifted start and end. The tags themselves are unchanged.

### Correctness

On the demo input all ten Linux binaries write the same 59,886 records under the
defaults, and, with duplicates kept and strand tags off, 1.19.1's record stream:
seven on the packaging host, and the three znver4 binaries, which need AVX-512,
on an AMD EPYC 9474F (Zen 4) machine, unpacked from their archive. The checks
are listed in `RELEASE_NOTES.md`.

### Known limitations

* The **Installing T2GD** topic in the built-in manual predates this release:
  it names three Linux builds where there are now four archives and a static
  binary, and gives its example filenames as `t2gd-1.19.0-...`. `INSTALL.md`
  and the `RUN_LINUX.txt` page in each archive are current. The manual is
  compiled into the executable, and this release keeps the measured binaries
  byte for byte.
* The screenshot of the Help tab in the built-in manual still shows nine topics
  where the manual carries fourteen, and the About tab picture still reads
  v1.18.0. Both are pictures only.

## 1.19.1 "Shenlong" (2026-08-09)

Build recipe only. There is no source change, no change to the command line
surface, and no change to any record T2GD writes. If you are running 1.19.0,
nothing here requires you to change anything.

Link time optimisation (`--flto=full`) is removed from the five shipping
release recipes. The codename does not advance, because it is the same source
tree and a new codename would imply new software.


### Correctness

All 18 record stream digest groups agreed across every build tested, with zero
mismatches, on both x86-64 and Apple Silicon. Removing LTO changes no output.

### Windows: an installer is offered for the first time

Alongside the portable zip there is now
`t2gd-1.19.1-Shenlong-windows-x86_64-setup.exe`. It installs the same tree the
zip carries, under `Program Files`, with Start-menu and optional desktop
shortcuts and an option to put the install directory on `PATH`. The zip remains
the primary Windows download and nothing is lost by preferring it; the installer
exists so that Windows users who expect one are not asked to think about where
to unpack a folder.

### Known limitations

* The **Installing T2GD** topic in the built-in manual gives its example
  filenames as `t2gd-1.19.0-...`. The instructions are right; only the example
  version string is stale. The manual is compiled into the executable, so
  correcting it would mean rebuilding all five platforms and re-establishing
  every checksum in this release, which is not worth a version number in a
  sample unpack command. `INSTALL.md` in the repository carries the correct
  names, as does the release download page.
* The screenshot of the Help tab in the built-in manual still predates the last
  five topics, so it shows a nine-topic navigator where the manual carries
  fourteen, and the About tab picture still reads v1.18.0 "Fafnir". Both are
  pictures only. The manual text, the live navigator and the real About tab are
  all correct.

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

**macOS now ships `T2GD.app`.** Finder does not launch a bare executable
directly. It hands it to Terminal, which opens a window and runs the program
inside it. Drag the bundle to `/Applications` and open it from there; it
launches on its own. The bare `t2gd` is still in the archive for anyone who
wants it from a shell.

### The built-in manual matches the packaging again

The *Installing T2GD* topic inside the binary had drifted. It described a
`t2gd-cli-static` binary and a `generic` build variant, neither of which has
ever been in a release; it claimed a macOS `x86_64` build that does not exist;
and its unpack example named a directory the archives do not produce. It has
been rewritten from the artifacts and now agrees with `INSTALL.md`.

### Faster depth, faster BAM writing

These changes were developed under the number 1.18.1, which was never
released; the binaries built under it existed only for measurement. They ship
here.

* **`depth` and `coverage` are about 3× faster.**
* **BAM writing is about 1.9× faster.** libdeflate is statically linked; the
  shared library list is unchanged.
* **The compressed bytes differ from 1.18.0 but the records do not.**
  libdeflate and zlib both emit valid DEFLATE and make different, equally legal
  choices.

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
