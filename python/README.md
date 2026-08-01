# T2G reference implementation (Python)

`t2g_bam_converter.py` is the reference implementation of the transcriptome-to-genome
conversion method. Version 5.7.

This is the same method the compiled `t2gd` binary implements. It is published
so that the method is auditable and the results in the accompanying paper are
reproducible: it is the readable specification of what `t2gd` does, in about
1,500 lines of Python you can step through in a debugger.

For production work, use the binary. It is faster, it needs no Python and no
pysam, and it carries the rest of the toolkit. See the [main README](../README.md).

---

## What it does

Takes a BAM aligned against a transcriptome FASTA plus the GTF that defines
those transcript models, and writes a BAM in genome coordinates. Each alignment
is lifted onto the genome, its CIGAR split at every exon boundary it crosses,
and an `N` operation inserted for each intron.

For transcripts on the minus strand it flips `FLAG` `0x10`, reverse-complements
`SEQ`, reverses the qualities, and swaps the clip groups at the two ends. Base
modification tags (`MM`/`ML`) are deliberately *not* transformed: per the SAM
specification they are expressed relative to the original read orientation, not
to the stored `SEQ`, so passing them through unchanged is the correct behaviour.

## Requirements

- Python 3, developed and tested on 3.14. The code uses no syntax newer than
  3.6, but older interpreters are untested.
- [pysam](https://pysam.readthedocs.io/), tested against 0.24.0
- `tqdm`, optional, for progress bars

```bash
pip install pysam tqdm
```

Unlike the binary, this script does have dependencies. That difference is the
point of the binary.

## Quick start

```bash
python3 t2g_bam_converter.py \
    -g Homo_sapiens.GRCh38.114.gtf \
    -i transcriptome_aligned.bam \
    -o genome_aligned.bam \
    -t 8
```

`--help` lists the full option set. The ones you are most likely to need:

| flag | what it is for |
|---|---|
| `--strip-version` | your BAM `@SQ` names are versioned (`ENST00000456328.2`) but the GTF IDs are bare, or vice versa |
| `-t N` | worker processes |
| `--species human` | sets a sane maximum intron size; see `--max-intron` for the manual version |
| `--primary-only` | drop secondary alignments |
| `--no-pair-restore` | single-end data |
| `--validate` | extra consistency checks on the output |

### A note on `--strip-version`

Transcriptome BAMs produced against an Ensembl cDNA FASTA carry versioned
transcript IDs in `@SQ`, while the matching GTF carries bare IDs. This script
will match nothing at all unless you pass `--strip-version`. The binary
reconciles the two forms itself and needs no flag. If a run reports that no
transcripts were found, this is almost always why.

## Differences from the binary

| | this script | `t2gd` |
|---|---|---|
| dependencies | Python, pysam | none, static binary |
| versioned vs bare transcript IDs | needs `--strip-version` | automatic |
| secondary-alignment tag recovery | not implemented | on by default, `--no-recover-secondary-tags` to disable |
| memory ceiling | none; scales with input | `--disk-spill` and `T2GD_CONVERT_BUDGET_MB` give a bounded footprint |
| output record order | nondeterministic across runs | deterministic |
| output file bytes | not reproducible | records reproducible, BGZF framing varies |
| rest of the toolkit | not included | 36 subcommands |

On matched settings the two agree read for read on `QNAME`, `FLAG`, `RNAME`,
`POS`, `MAPQ` and `CIGAR`. The binary is several times faster; the figures are
in the paper and in the built-in **Performance and resources** topic.

Output record order being nondeterministic is worth restating, because it
catches people out: this script writes records as worker batches complete, so
two runs on the same input give the same records in a different order. Compare
outputs with a sort or a per-record digest, never with `cmp`.

Neither tool produces a byte-identical BAM across runs, and for `t2gd` that is
purely the BGZF block layout: two `t2gd` runs on the same input give byte-identical
*record streams* (`samtools view` output) and different file checksums. So
checksum a `samtools view` stream, not the `.bam`, if you want to compare runs.

## Aux tags

Every tag already on the input record is carried through, including
array-valued (SAM type `B`) tags such as `ML` and `pa`. A tag that cannot be
written is logged once per tag per worker rather than dropped in silence. The
tags the conversion itself adds are listed in the module docstring and in
`--help`.

## Licence

CC BY-NC-ND 4.0, the same licence as the rest of this repository. See
[LICENSE](../LICENSE).

Published for reading, running and citing, not for forking: the NoDerivatives
term means you may not distribute a modified copy. If you need to modify it, or
to use it commercially, ask us rather than forking quietly. Contact details are
in the [main README](../README.md).

Copyright (c) 2026 Biocodecs, Arnaroo Ribologicals, COMPASS.
