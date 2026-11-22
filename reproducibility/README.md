# Reproducibility

This directory documents the supplementary code and data package that
accompanies the T2G manuscript. The package itself is a release asset, not a
tracked part of this repository: it is tens of megabytes, and archives of that
size do not belong in git history.

## The package

Download `T2GD_supplementary_code_and_data.tar.gz` from the
[v1.22.0 release](https://github.com/Arnaroo/T2GD/releases/tag/v1.22.0). The
same file is submitted to the journal as Supplementary Information with the
revised manuscript, so either copy will do. The package of the first
submission, which went with v1.19.1, stays attached to the
[v1.19.1 release](https://github.com/Arnaroo/T2GD/releases/tag/v1.19.1).

| | |
|---|---|
| File | `T2GD_supplementary_code_and_data.tar.gz` |
| Size | 46,129,284 bytes (44 MiB) |
| SHA-256 | `955a0001a42639faae01444dabbdcb87d3b5834e06039726af887b254b58fe3a` |
| Contents | 495 files, 60,891,595 bytes unpacked, in one folder, `T2GD_supplementary_code_and_data/` |

The hash is recorded here rather than in `release/SHA256SUMS`, because that file
is regenerated over the platform archives by the release script and would
drop this entry on the next run.

```sh
echo '955a0001a42639faae01444dabbdcb87d3b5834e06039726af887b254b58fe3a  T2GD_supplementary_code_and_data.tar.gz' | sha256sum -c -
tar xzf T2GD_supplementary_code_and_data.tar.gz
cd T2GD_supplementary_code_and_data
```

## What is inside

One folder per section of the supplement, numbered as the supplement numbers
them, and the Python reference. The revision added the last four sections;
`README.md` inside the package says what changed in the others.

| Path | Section of the supplement | Files |
|---|---|---:|
| `s4.1_long_read/` | 4.1 Long-read direct RNA | 35 |
| `s4.2_paired_end/` | 4.2 Paired-end short reads | 36 |
| `s4.3_footprint/` | 4.3 Ribosome footprinting | 80 |
| `s4.4_runtime/` | 4.4 Runtime scalability | 26 |
| `s4.5_toolkit/` | 4.5 Auxiliary toolkit | 23 |
| `s4.6_pond/` | 4.6 RBP experiment reanalysis | 43 |
| `s4.7_simulation/` | 4.7 Reads of known origin | 32 |
| `s4.8_rsem/` | 4.8 rsem-tbam2gbam on the same inputs | 75 |
| `s4.9_multimap/` | 4.9 Isoform multimappers after the lift | 101 |
| `s4.10_threads/` | 4.10 Thread scaling and region-level conversion | 39 |
| `python/` | The Python reference implementation, version 5.8 | 1 |

Each section holds a `harness/` of the scripts that ran the benchmark, a
`results/` of the per-read and per-gene summary files they produced, and the
figure scripts that turn those summaries into the panels in the supplement.
Sections that the revision ran again also hold `harness_revision/` and
`results_revision/`, or keep the first version's inputs in `results_submitted/`.

Three index files sit at the top level:

- **`FIGURES.tsv`** names the generator and the inputs of every figure, table
  and quoted number of the supplement, 52 items, and states item by item
  whether the script shipped here reproduces it exactly. Four figure scripts
  are shipped whose inputs were not retained, so they do not run from the
  package alone; the status column names them.
- **`DATASETS.tsv`** lists every dataset used, in two groups: the sequencing
  runs with their archive accessions, and the reference builds they were
  aligned to with their release identifiers. The reference rows record the
  annotation and assembly behind each result, including a checksum for the
  human annotation, since every count reported is a count of that file's
  features.
- **`MANIFEST.tsv`** gives the path, size and SHA-256 of every file in the
  package.

To verify the unpacked tree against the manifest:

```sh
tail -n +2 MANIFEST.tsv | while IFS=$'\t' read -r p b s; do
    echo "$s  $p"
done | sha256sum -c --quiet
```

## Running the figure scripts

The figure scripts resolve their inputs and outputs relative to their own
location and take no arguments.

```sh
cd s4.1_long_read
python3 make_fig_AURKAIP1_m5C_isoform_resolution.py
```

They need `numpy` and `matplotlib`. The two transcript-level scripts under
`s4.2_paired_end/` also need `pandas`, and the replicate correlation one `scipy`. The harness scripts under each `harness/` need
`pysam`, and are shipped as the record of how each benchmark was run rather
than as scripts expected to run unmodified elsewhere: they carry scheduler
directives and cluster paths from the machines the work was done on.

`README.md` inside the package repeats this and adds the per-section detail.

## What is not included

Alignment files. The BAMs behind these results run to hundreds of gigabytes.
They are reconstructible from the deposited reads and the references named in
`DATASETS.tsv`, using the procedures in the supplement's preprocessing section.
Everything downstream of alignment is in the package.

One alignment did not survive and is treated as a recomputation rather than a
reproduction throughout: the STAR footprint run behind the originally published
gene detection and composition results was lost, and the STAR arm of that
comparison was rebuilt on an Ensembl 115 realignment. The supplement says so at
the point where those numbers are quoted.

The D source tree is not part of the release. This is stated in
[RELEASE_NOTES.md](../RELEASE_NOTES.md) and in the manuscript.

## Relation to this repository

`python/t2g_bam_converter.py` in the package is byte-identical to
[`python/t2g_bam_converter.py`](../python/t2g_bam_converter.py) here. It is
duplicated into the package so that the reference implementation can be read
alongside the harnesses that measure it, without a second download.

The compiled tool the manuscript benchmarks is the release itself. The version
the revised manuscript reports is **v1.22.0 "Vritra"**, archived on Zenodo
with its release archives as well as the repository contents, at the version
DOI [10.5281/zenodo.24433505](https://doi.org/10.5281/zenodo.24433505) under the
concept DOI
[10.5281/zenodo.21744718](https://doi.org/10.5281/zenodo.21744718). Its
`linux-generic/t2gd-cli-static` is byte for byte the binary the revised
manuscript's measurements were made with. The first submission reported
v1.19.1 "Shenlong", archived at
[10.5281/zenodo.22016829](https://doi.org/10.5281/zenodo.22016829); that
snapshot holds the repository contents only, not the release assets.
