# Reproducibility

This directory documents the supplementary code and data package that
accompanies the T2G manuscript. The package itself is a release asset, not a
tracked part of this repository: it is 45 MB, and archives of that size do not
belong in git history.

## The package

Download `T2GD_supplementary_code_and_data.tar.gz` from the
[v1.19.1 release](https://github.com/Arnaroo/T2GD/releases/tag/v1.19.1). The
same file is submitted to the journal as Supplementary Information, so either
copy will do.

| | |
|---|---|
| File | `T2GD_supplementary_code_and_data.tar.gz` |
| Size | 45,175,352 bytes |
| SHA-256 | `738d7bee3b849bde195788344e7184d312e57cfd610904c15233e6225dd91298` |
| Contents | 137 files in 24 directories, 54 MB unpacked |

The hash is recorded here rather than in `release/SHA256SUMS`, because that file
is regenerated over the six platform archives by the release script and would
drop this entry on the next run.

```sh
echo '738d7bee3b849bde195788344e7184d312e57cfd610904c15233e6225dd91298  T2GD_supplementary_code_and_data.tar.gz' | sha256sum -c -
tar xzf T2GD_supplementary_code_and_data.tar.gz
cd T2GD_supplementary_code_and_data
```

## What is inside

| Path | Section of the supplement | Files |
|---|---|---:|
| `s4.1_long_read/` | ONT direct RNA sequencing | 8 |
| `s4.2_paired_end/` | Paired-end short-read RNA sequencing | 20 |
| `s4.3_footprint/` | Ribosome footprinting | 37 |
| `s4.4_runtime/` | Runtime and memory | 26 |
| `s4.5_toolkit/` | Toolkit parity and tag fidelity | 23 |
| `s4.6_pond/` | Multi-mapping and aligner comparison | 18 |
| `python/` | The Python reference implementation | 1 |

Each section holds a `harness/` of the scripts that ran the benchmark, a
`results/` of the per-read and per-gene summary files they produced, and the
figure scripts that turn those summaries into the panels in the supplement.

Three index files sit at the top level:

- **`FIGURES.tsv`** names the generator for every numbered figure and states,
  figure by figure, whether it reruns from the package. Fourteen of the
  eighteen numbered figures are reproduced byte for byte from the summary file
  shipped beside the script. For the remaining four the generator is shipped
  but its inputs were not retained, either because they were intermediate
  tables that were never archived or because they run to hundreds of megabytes.
  `FIGURES.tsv` names those four.
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

They need `numpy` and `matplotlib`. Two scripts under `s4.2_paired_end/` also
need `pandas` and `scipy`. The harness scripts under each `harness/` need
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
the manuscript reports is **v1.19.1 "Shenlong"**, archived at
[10.5281/zenodo.22016829](https://doi.org/10.5281/zenodo.22016829) under the
concept DOI [10.5281/zenodo.21744718](https://doi.org/10.5281/zenodo.21744718).
Note that Zenodo archives the GitHub source zipball, so the DOI covers the
repository contents and not the release assets; take the assets from the
release page.
