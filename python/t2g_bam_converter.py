#!/usr/bin/env python3
"""
Transcriptome to Genome BAM Converter - Version 5.7
Converts BAM files aligned to transcriptome coordinates to genome coordinates.

Copyright (c) 2026 the T2G authors.

This file is licensed under the Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International licence
(CC BY-NC-ND 4.0).  See the LICENSE file distributed with this software,
or https://creativecommons.org/licenses/by-nc-nd/4.0/ for the full terms.

What this program does
----------------------
A transcriptome alignment places a read on a spliced mRNA, so its coordinates
mean nothing to a genome browser or to any tool that expects chromosomes.  This
program walks each alignment back out through the exon structure declared in a
GTF, emitting an N operation wherever the walk crosses an intron, and writes the
result as a genome-space BAM.

Reads on minus-strand transcripts
---------------------------------
A transcript on the minus strand runs backwards relative to the genome, so the
exon walk is traversed in reverse, FLAG 0x10 is flipped, the stored sequence is
reverse-complemented, the quality string is reversed, and the leading and
trailing clip operations are swapped so the CIGAR reads left to right on the
genome.  That combination is the correct SAM representation: a downstream tool
computes RC(SEQ) itself to compare against the forward reference, so SEQ and
FLAG must agree.

Base modification tags (MM, ML, MN) are deliberately left untransformed.  The
SAM specification expresses them relative to the original read as it came off
the sequencer, not relative to the SEQ stored in the record, so reversing them
alongside the sequence would corrupt them.  On the ONT validation fixture, SEQ
is identical between this converter and the compiled t2gd implementation across
all 12,161 primary reverse-strand records.

Pair restoration
----------------
Paired-end input is repaired after conversion without a separate script.  The
HI (hit-index) tag is used so that every alignment of a multimapper is paired
with the right partner, FLAG bits 0x2, 0x8 and 0x20 are recomputed, and the pk
tag records the outcome: 0 singleton, 1 same-transcript pair, 2 cross-transcript
pair.  --cross-transcript-pairs additionally pairs mates the aligner assigned to
different isoforms, clearing the "properly paired" bit (0x2) for those.
--no-pair-restore turns the whole pass off for single-end data.

Tag namespace
-------------
Custom tags use the lowercase two-character namespace the SAM specification
reserves for user-defined tags, which avoids collisions with the uppercase tags
emitted by BWA, STAR, HISAT2 and Bowtie2:

    tx  transcript ID
    gn  gene ID
    gs  genome 5' start
    ge  genome 3' end
    xl  mapped length (exons)
    xp  mapped span including introns
    xi  spans-intron flag
    im  max intron size
    ro  read orientation, +1 forward or -1 reverse
    pk  pair class
    ds  5' distance from gene start
    de  5' distance from gene end
    es  3' distance from gene start
    ee  3' distance from gene end

Tags already present on the input record are carried through, including
array-valued (SAM type B) tags such as ML and pa.  A tag that cannot be written
is reported once per tag per worker rather than dropped in silence.

Architecture note: why two passes?
-------------------------------------
Conversion (pass 1) is embarrassingly parallel: each read is converted
independently.  Parallel workers receive reads in arbitrary order, so two mates
of the same pair will typically land in different batches on different CPUs.
There is no way to match them *during* conversion without either sorting the
input by name first (losing parallelism) or sharing mutable state across
processes (very expensive).  The pairing pass (pass 2) is a single fast O(N)
sequential scan with O(unmatched) memory.  Both passes are hidden inside one
command from the user's perspective.

Multimapper pairing strategy
-----------------------------
  Pass A, same-transcript: key = (qname, tx, HI)
    Pairs mates that mapped concordantly to the same transcript at the same
    alignment index.  This is the standard case.
  Pass B, cross-transcript (--cross-transcript-pairs): key = (qname, HI)
    After pass A, any unmatched read is placed in a cross-transcript pool keyed
    by (qname, HI).  When a partner with the same qname+HI arrives (possibly
    mapping to a different transcript), they are paired.  This correctly handles
    discordant pairs and multimappers across isoforms.
  Singletons: reads still unmatched at EOF.
"""

import argparse
import sys
import os
import re
import gzip
import tempfile
import shutil
import time
import logging
import threading
import multiprocessing as mp
from collections import defaultdict, Counter, deque
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
import pysam
import queue
import glob
import random

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Note: install tqdm for progress bars:  pip install tqdm")

logger = logging.getLogger(__name__)

SPECIES_INTRON_SIZES = {
    'human':     500_000,
    'mouse':     500_000,
    'fly':       100_000,
    'worm':       50_000,
    'yeast':       5_000,
    'plant':     750_000,
    'zebrafish': 500_000,
    'custom':    None,
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PairRestorationConfig:
    enabled: bool = True
    cross_transcript: bool = False
    unpaired_output: Optional[str] = None
    ambiguous_output: Optional[str] = None
    summary: Optional[str] = None
    tag: str = "tx"   # SAM tag carrying transcript ID


@dataclass
class ValidationStats:
    total_validated: int = 0
    perfect_matches: int = 0
    cigar_mismatches: int = 0
    strand_errors: int = 0
    failed_validations: int = 0
    warnings: List[str] = field(default_factory=list)

    def add_warning(self, msg):
        if len(self.warnings) < 100:
            self.warnings.append(msg)

    def report(self):
        if self.total_validated == 0:
            return "No reads validated"
        acc = 100 * self.perfect_matches / self.total_validated
        lines = [
            f"\n{'='*50}", "VALIDATION REPORT", f"{'='*50}",
            f"Total validated      : {self.total_validated:,}",
            f"Perfect matches      : {self.perfect_matches:,} ({acc:.2f}%)",
            f"CIGAR mismatches     : {self.cigar_mismatches:,}",
            f"Strand errors        : {self.strand_errors:,}",
            f"Failed validations   : {self.failed_validations:,}",
            f"{'='*50}",
        ]
        if self.warnings:
            lines.append("Sample warnings (first 10):")
            lines += [f"  - {w}" for w in self.warnings[:10]]
        return "\n".join(lines)


@dataclass
class MissingTranscriptStats:
    total_reads: int = 0
    unique_transcripts: Set[str] = field(default_factory=set)
    forward_strand: int = 0
    reverse_strand: int = 0
    primary_alignments: int = 0
    secondary_alignments: int = 0
    supplementary_alignments: int = 0
    alignment_counts: Counter = field(default_factory=Counter)

    def add_read(self, transcript_id, flag, nh_tag=None):
        self.total_reads += 1
        self.unique_transcripts.add(transcript_id)
        if flag & 0x10:
            self.reverse_strand += 1
        else:
            self.forward_strand += 1
        if flag & 0x100:
            self.secondary_alignments += 1
        elif flag & 0x800:
            self.supplementary_alignments += 1
        else:
            self.primary_alignments += 1
        self.alignment_counts[nh_tag if nh_tag is not None else 1] += 1

    def report(self):
        if self.total_reads == 0:
            return ""
        t = self.total_reads
        lines = [
            f"\nMissing transcript statistics:",
            f"  Total reads           : {t:,}",
            f"  Unique transcripts    : {len(self.unique_transcripts):,}",
            f"  Forward / Reverse     : {self.forward_strand:,} / {self.reverse_strand:,}",
            f"  Primary alignments    : {self.primary_alignments:,}",
            f"  Secondary             : {self.secondary_alignments:,}",
            f"  Supplementary         : {self.supplementary_alignments:,}",
        ]
        if self.alignment_counts:
            lines.append("  NH distribution:")
            for nh in sorted(self.alignment_counts):
                cnt = self.alignment_counts[nh]
                lines.append(f"    NH={nh}: {cnt:,} ({100*cnt/t:.1f}%)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Genomic data structures (Exon, Transcript)
# ---------------------------------------------------------------------------

@dataclass
class Exon:
    chrom: str
    start: int   # 0-based
    end: int     # exclusive
    strand: str

    @property
    def length(self):
        return self.end - self.start


@dataclass
class Transcript:
    transcript_id: str
    gene_id: str
    chrom: str
    strand: str
    exons: List[Exon]
    exon_cumulative_lengths: List[int] = field(default_factory=list)
    total_length: int = 0
    gene_start: int = 0
    gene_end: int = 0
    gene_span: int = 0
    transcript_start: int = 0
    transcript_end: int = 0

    def __post_init__(self):
        self.exons.sort(key=lambda e: e.start)
        if self.exons:
            self.transcript_start = min(e.start for e in self.exons)
            self.transcript_end   = max(e.end   for e in self.exons)
        tx_exons = list(reversed(self.exons)) if self.strand == '-' else self.exons
        cum, lengths = 0, []
        for ex in tx_exons:
            lengths.append(cum)
            cum += ex.length
        self.exon_cumulative_lengths = lengths
        self.total_length = cum
        self.transcript_exons = tx_exons

    def transcript_region_to_genome(self, tx_start, tx_end):
        """Return list of (chrom, g_start, g_end, length) in genomic order."""
        if tx_start < 0 or tx_end > self.total_length or tx_start >= tx_end:
            return []
        exons, cumls = self.transcript_exons, self.exon_cumulative_lengths
        # find first exon
        start_idx = 0
        for i, (ex, cl) in enumerate(zip(exons, cumls)):
            if tx_start < cl + ex.length:
                start_idx = i
                break
        regions, cur, rem = [], tx_start, tx_end - tx_start
        for i in range(start_idx, len(exons)):
            if rem <= 0:
                break
            ex, cl = exons[i], cumls[i]
            off = cur - cl if i == start_idx else 0
            rlen = min(rem, ex.length - off)
            if self.strand == '+':
                gs, ge = ex.start + off, ex.start + off + rlen
            else:
                ge, gs = ex.end - off, ex.end - off - rlen
            regions.append((self.chrom, gs, ge, rlen))
            rem -= rlen
            cur += rlen
        if self.strand == '-':
            regions.reverse()
        return regions

    def calculate_position_metrics(self, genome_start, genome_end):
        if self.strand == '+':
            return dict(
                start_from_gene_start = genome_start - self.gene_start,
                start_from_gene_end   = self.gene_end - genome_start,
                end_from_gene_start   = genome_end - self.gene_start,
                end_from_gene_end     = self.gene_end - genome_end,
            )
        else:
            return dict(
                start_from_gene_start = self.gene_end - genome_end,
                start_from_gene_end   = genome_end - self.gene_start,
                end_from_gene_start   = self.gene_end - genome_start,
                end_from_gene_end     = genome_start - self.gene_start,
            )

# ---------------------------------------------------------------------------
# PairRestorator — single-pass, HI-aware pairing
# ---------------------------------------------------------------------------

class PairRestorator:
    """
    Single-pass pair restoration with full multimapper support.

    Pairing hierarchy
    -----------------
    1. Same-transcript (always):
         key = (qname, XT-tag, HI-tag)
         Pairs concordant mates on the same transcript at the same alignment index.

    2. Cross-transcript (--cross-transcript-pairs):
         key = (qname, HI-tag)
         After same-transcript matching, unmatched reads are pooled by
         (qname, HI).  A partner arriving later with the same qname+HI is
         paired even if its XT differs.  This correctly handles:
           * Discordant pairs assigned to different isoforms of the same gene.
           * Multimappers: R1-HI=2 pairs with R2-HI=2, etc.

    HI fallback
    -----------
    If the aligner did not write an HI tag (rare), HI defaults to 0 for
    unique mappers (NH=1) and to a position-derived hash for multimappers,
    so pairing degrades gracefully to the FIFO behaviour of v4.x.

    FLAG corrections applied
    ------------------------
      0x1  is_paired       — set for all paired reads
      0x2  properly paired — set only for same-transcript pairs, same chrom
      0x8  mate unmapped   — reflects real post-liftover status
      0x20 mate reverse    — reflects mate's actual strand after liftover
    """

    def __init__(self, config: PairRestorationConfig):
        self.cfg = config

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _hi(read: pysam.AlignedSegment) -> int:
        """Return HI tag or a sensible default."""
        if read.has_tag("HI"):
            return int(read.get_tag("HI"))
        # For unique mappers NH==1, use 0; for multimappers hash gs+strand
        nh = int(read.get_tag("NH")) if read.has_tag("NH") else 1
        if nh == 1:
            return 0
        gs = int(read.get_tag("gs")) if read.has_tag("gs") else read.reference_start
        return hash((gs, read.flag & 0x10)) & 0xFFFF

    @staticmethod
    def _xs(read: pysam.AlignedSegment) -> int:
        return int(read.get_tag("gs")) if read.has_tag("gs") else read.reference_start

    @staticmethod
    def _compute_tlen(r1, r2):
        if r1.is_unmapped or r2.is_unmapped:
            return 0, 0
        if r1.reference_id != r2.reference_id:
            return 0, 0
        xs1 = PairRestorator._xs(r1)
        xs2 = PairRestorator._xs(r2)
        xp1 = int(r1.get_tag("xp")) if r1.has_tag("xp") else r1.query_alignment_length
        xp2 = int(r2.get_tag("xp")) if r2.has_tag("xp") else r2.query_alignment_length
        xe1, xe2 = xs1 + xp1, xs2 + xp2
        if xs1 <= xs2:
            lxs, lxe, rxs, rxe, l_is_r1 = xs1, xe1, xs2, xe2, True
        else:
            lxs, lxe, rxs, rxe, l_is_r1 = xs2, xe2, xs1, xe1, False
        tlen = (lxe - lxs) + max(rxs - lxe, 0) + (rxe - rxs)
        return (+tlen, -tlen) if l_is_r1 else (-tlen, +tlen)

    @staticmethod
    def _fix_flags(r1, r2, pair_type):
        """Set 0x1/0x2/0x8/0x20 correctly on both mates."""
        same_chrom = (r1.reference_id == r2.reference_id
                      and not r1.is_unmapped and not r2.is_unmapped)
        properly = (pair_type == 'same_transcript' and same_chrom)
        for read, mate in ((r1, r2), (r2, r1)):
            read.flag |= 0x1                          # is_paired
            if properly: read.flag |=  0x2
            else:        read.flag &= ~0x2
            if mate.is_unmapped: read.flag |=  0x8
            else:                read.flag &= ~0x8
            if mate.flag & 0x10: read.flag |=  0x20
            else:                read.flag &= ~0x20

    @staticmethod
    def _restore_rnext_pnext_tlen(r1, r2, tlen_r1, tlen_r2):
        for read, mate in ((r1, r2), (r2, r1)):
            if mate.is_unmapped:
                read.next_reference_id = -1
            elif read.reference_id == mate.reference_id:
                read.next_reference_id = read.reference_id
            else:
                read.next_reference_id = mate.reference_id
            read.next_reference_start = (
                PairRestorator._xs(mate) if not mate.is_unmapped else 0)
        r1.template_length = tlen_r1
        r2.template_length = tlen_r2

    def _write_pair(self, ra, rb, pair_type, out_bam, summary_rows):
        """Finalize and write a matched pair."""
        # Respect FLAG 0x40/0x80 for R1/R2 assignment; fall back to XS order
        a_r1 = bool(ra.flag & 0x40)
        b_r1 = bool(rb.flag & 0x40)
        if a_r1 and not b_r1:
            r1, r2 = ra, rb
        elif b_r1 and not a_r1:
            r1, r2 = rb, ra
        else:
            r1, r2 = (ra, rb) if self._xs(ra) <= self._xs(rb) else (rb, ra)

        tlen_r1, tlen_r2 = self._compute_tlen(r1, r2)
        self._restore_rnext_pnext_tlen(r1, r2, tlen_r1, tlen_r2)
        self._fix_flags(r1, r2, pair_type)
        xk = 1 if pair_type == 'same_transcript' else 2
        for r in (r1, r2):
            try: r.set_tag("pk", xk, "i")
            except Exception: pass
        out_bam.write(r1)
        out_bam.write(r2)

        if self.cfg.summary:
            xt1 = r1.get_tag(self.cfg.tag) if r1.has_tag(self.cfg.tag) else "?"
            xt2 = r2.get_tag(self.cfg.tag) if r2.has_tag(self.cfg.tag) else "?"
            xt_label = xt1 if xt1 == xt2 else f"{xt1}/{xt2}"
            summary_rows.append((
                r1.query_name, xt_label, pair_type,
                r1.reference_name or "*", self._xs(r1) + 1,
                r2.reference_name or "*", self._xs(r2) + 1,
                tlen_r1,
            ))

    # ------------------------------------------------------------------ main loop

    def restore_pairs(self, input_bam: str, output_bam: str) -> Dict[str, int]:
        """
        Single-pass restoration.  Returns statistics dict.

        Waiting rooms
        -------------
        same_tx_waiting  : {(qname, XT, HI) -> read | None(sentinel)}
        cross_tx_waiting : {(qname, HI)     -> deque of reads}   (opt.)
        """
        cfg = self.cfg
        same_tx_waiting: Dict = {}
        cross_tx_waiting: Dict = defaultdict(deque) if cfg.cross_transcript else None

        stats: Dict[str, int] = defaultdict(int)
        summary_rows = []

        with pysam.AlignmentFile(input_bam, "rb") as bam_in:
            hdr = bam_in.header
            with pysam.AlignmentFile(output_bam, "wb", header=hdr) as out_bam:
                unpaired_bam = (pysam.AlignmentFile(cfg.unpaired_output, "wb", header=hdr)
                                if cfg.unpaired_output else None)
                ambiguous_bam = (pysam.AlignmentFile(cfg.ambiguous_output, "wb", header=hdr)
                                 if cfg.ambiguous_output else None)
                try:
                    for read in bam_in.fetch(until_eof=True):
                        stats['total'] += 1
                        qname = read.query_name

                        # Pass-through: not paired or no XT tag
                        if not (read.flag & 0x1) or not read.has_tag(cfg.tag):
                            stats['passthrough'] += 1
                            out_bam.write(read)
                            continue

                        xt = str(read.get_tag(cfg.tag))
                        hi = self._hi(read)

                        # ---- same-transcript pool ----
                        key_same = (qname, xt, hi)
                        if key_same in same_tx_waiting:
                            parked = same_tx_waiting.pop(key_same)
                            if parked is None:              # sentinel: >2 reads
                                stats['ambiguous'] += 1
                                if ambiguous_bam:
                                    ambiguous_bam.write(read)
                                continue
                            # optionally remove from cross-tx pool
                            if cfg.cross_transcript:
                                dq = cross_tx_waiting.get((qname, hi))
                                if dq:
                                    try: dq.remove(parked)
                                    except ValueError: pass
                                    if not dq:
                                        del cross_tx_waiting[(qname, hi)]
                            self._write_pair(parked, read, 'same_transcript',
                                             out_bam, summary_rows)
                            stats['same_tx_pairs'] += 1
                            same_tx_waiting[key_same] = None  # sentinel

                        # ---- cross-transcript pool ----
                        elif cfg.cross_transcript:
                            key_cross = (qname, hi)
                            dq = cross_tx_waiting.get(key_cross)
                            # look for a read with complementary R1/R2 flag
                            partner = None
                            if dq:
                                cur_is_r1 = bool(read.flag & 0x40)
                                for i, candidate in enumerate(dq):
                                    cand_is_r1 = bool(candidate.flag & 0x40)
                                    if cand_is_r1 != cur_is_r1:
                                        partner = candidate
                                        del dq[i]
                                        if not dq:
                                            del cross_tx_waiting[key_cross]
                                        break
                            if partner is not None:
                                # also clean same_tx_waiting
                                p_xt = str(partner.get_tag(cfg.tag)) if partner.has_tag(cfg.tag) else ""
                                same_tx_waiting.pop((qname, p_xt, hi), None)
                                self._write_pair(partner, read, 'cross_transcript',
                                                 out_bam, summary_rows)
                                stats['cross_tx_pairs'] += 1
                            else:
                                # park in both pools
                                same_tx_waiting[key_same] = read
                                cross_tx_waiting[key_cross].append(read)

                        else:
                            # same-tx only: park and wait
                            same_tx_waiting[key_same] = read

                    # ---- EOF: flush remaining non-sentinel entries ----
                    flushed = set()
                    for key, parked in same_tx_waiting.items():
                        if parked is not None and id(parked) not in flushed:
                            flushed.add(id(parked))
                            stats['singletons'] += 1
                            try: parked.set_tag("pk", 0, "i")
                            except Exception: pass
                            if unpaired_bam:
                                unpaired_bam.write(parked)
                            else:
                                out_bam.write(parked)

                finally:
                    if unpaired_bam:  unpaired_bam.close()
                    if ambiguous_bam: ambiguous_bam.close()

        if cfg.summary and summary_rows:
            with open(cfg.summary, "w") as fh:
                fh.write("read_name\ttranscript_id\tpair_type\t"
                         "r1_chrom\tr1_pos\tr2_chrom\tr2_pos\ttlen\n")
                for row in summary_rows:
                    fh.write("\t".join(str(x) for x in row) + "\n")
            logger.info(f"  Pair summary written to: {cfg.summary}")

        return dict(stats)

# ---------------------------------------------------------------------------
# ChromosomeSizes + GTFParser (unchanged from v4.7)
# ---------------------------------------------------------------------------

class ChromosomeSizes:
    def __init__(self, source=None):
        self.sizes = {}
        if source:
            self._load(source)

    def _load(self, source):
        with open(source) as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    self.sizes[parts[0]] = int(parts[1])
        logger.debug(f"Loaded sizes for {len(self.sizes)} chromosomes")

    def get_size(self, chrom, default=300_000_000):
        return self.sizes.get(chrom, default)


class GTFParser:
    def __init__(self, gtf_file, threads=1, strip_version=False):
        self.gtf_file = gtf_file
        self.threads = threads
        self.strip_version = strip_version
        self.transcripts = {}
        self._parse_gtf()

    def _sv(self, tid):
        return tid.split('.')[0]

    def _parse_gtf(self):
        logger.info(f"Parsing GTF: {self.gtf_file}")
        gz = self.gtf_file.endswith('.gz')
        if self.threads > 1:
            self._parse_parallel(gz)
        else:
            self._parse_serial(gz)

    def _open(self, gz):
        import gzip as _gz
        return _gz.open(self.gtf_file, 'rt') if gz else open(self.gtf_file)

    def _parse_serial(self, gz):
        info = defaultdict(lambda: {'exons': []})
        with self._open(gz) as f:
            for line in f:
                if line.startswith('#'): continue
                p = self._parse_line(line)
                if p:
                    tid, gid, chrom, strand, exon = p
                    if 'gene_id' not in info[tid]:
                        info[tid].update(gene_id=gid, chrom=chrom, strand=strand)
                    info[tid]['exons'].append(exon)
        self._build(info)

    def _parse_parallel(self, gz):
        chunks, chunk = [], []
        with self._open(gz) as f:
            for line in f:
                if not line.startswith('#'):
                    chunk.append(line)
                    if len(chunk) >= 100_000:
                        chunks.append(chunk); chunk = []
        if chunk: chunks.append(chunk)
        with mp.Pool(self.threads) as pool:
            results = pool.map(self._proc_chunk, chunks)
        info = defaultdict(lambda: {'exons': []})
        for part in results:
            for tid, d in part.items():
                if 'gene_id' not in info[tid]:
                    info[tid].update(gene_id=d['gene_id'], chrom=d['chrom'], strand=d['strand'])
                info[tid]['exons'].extend(d['exons'])
        self._build(info)

    def _proc_chunk(self, lines):
        info = defaultdict(lambda: {'exons': []})
        for line in lines:
            p = self._parse_line(line)
            if p:
                tid, gid, chrom, strand, exon = p
                if 'gene_id' not in info[tid]:
                    info[tid].update(gene_id=gid, chrom=chrom, strand=strand)
                info[tid]['exons'].append(exon)
        return dict(info)

    def _parse_line(self, line):
        f = line.strip().split('\t')
        if len(f) < 9: return None
        if f[2] not in ('exon','CDS','UTR','five_prime_utr','three_prime_utr'): return None
        attr = {}
        for a in f[8].strip().split(';'):
            m = re.search(r'(\w+)\s+"?([^"]+)"?', a.strip())
            if m: attr[m.group(1)] = m.group(2).strip('"')
        if 'transcript_id' not in attr: return None
        tid = attr['transcript_id']
        gid = attr.get('gene_id', 'unknown')
        return tid, gid, f[0], f[6], Exon(f[0], int(f[3])-1, int(f[4]), f[6])

    def _build(self, info):
        logger.info("Building transcript models …")
        tmp = {}; g2tx = defaultdict(list)
        for tid, d in info.items():
            if not d['exons']: continue
            merged = self._merge(d['exons'])
            ftid = self._sv(tid) if self.strip_version else tid
            tx = Transcript(ftid, d['gene_id'], d['chrom'], d['strand'], merged)
            tmp[ftid] = tx
            g2tx[d['gene_id']].append(tx)
        for txs in g2tx.values():
            all_ex = [e for tx in txs for e in tx.exons]
            gs, ge = min(e.start for e in all_ex), max(e.end for e in all_ex)
            for tx in txs:
                tx.gene_start, tx.gene_end, tx.gene_span = gs, ge, ge-gs
        self.transcripts = tmp
        logger.info(f"Parsed {len(tmp)} transcripts from {len(g2tx)} genes")

    def _merge(self, exons):
        exons = sorted(exons, key=lambda e: e.start)
        merged = [exons[0]]
        for ex in exons[1:]:
            last = merged[-1]
            if ex.start <= last.end:
                merged[-1] = Exon(ex.chrom, last.start, max(last.end, ex.end), ex.strand)
            else:
                merged.append(ex)
        return merged

    def get_transcript(self, tid):
        if tid in self.transcripts: return self.transcripts[tid]
        base = tid.split('.')[0]
        for k, tx in self.transcripts.items():
            if k.split('.')[0] == base: return tx
        return None

# ---------------------------------------------------------------------------
# Worker-process globals and coordinate conversion (from v4.7)
# ---------------------------------------------------------------------------

worker_transcripts = None
worker_transcript_lookup = None
worker_max_intron_size = 500_000
worker_warn_intron_size = 100_000
worker_filter_secondary = False
worker_direct = False
worker_preserve_cigar_ops = True


def init_worker(tx_dict, lookup, max_intron, warn_intron, filt_sec, direct, preserve):
    global worker_transcripts, worker_transcript_lookup
    global worker_max_intron_size, worker_warn_intron_size
    global worker_filter_secondary, worker_direct, worker_preserve_cigar_ops
    worker_transcripts = {tid: Transcript(**d) for tid, d in tx_dict.items()}
    worker_transcript_lookup = lookup
    worker_max_intron_size  = max_intron
    worker_warn_intron_size = warn_intron
    worker_filter_secondary = filt_sec
    worker_direct           = direct
    worker_preserve_cigar_ops = preserve


def _get_transcript(tid):
    tx = worker_transcripts.get(tid)
    if tx: return tx
    alt = worker_transcript_lookup.get(tid)
    if alt: return worker_transcripts.get(alt)
    base = tid.split('.')[0]
    alt = worker_transcript_lookup.get(base)
    if alt: return worker_transcripts.get(alt)
    return None


def process_read_batch(args):
    batch_reads, min_mapq, batch_id = args
    results, stats = [], defaultdict(int)
    missing_tx, missing_details = set(), []
    intron_warn = Counter()

    for rd in batch_reads:
        stats['total'] += 1
        if worker_filter_secondary and (rd['flag'] & 0x100):
            stats['secondary_filtered'] += 1; continue
        if worker_direct and (rd['flag'] & 0x10):
            stats['reverse_filtered'] += 1; continue
        if rd['mapping_quality'] < min_mapq:
            stats['low_mapq_skipped'] += 1; continue
        if rd['is_unmapped']:
            stats['unmapped'] += 1; continue

        tx = _get_transcript(rd['reference_name'])
        if tx is None:
            missing_tx.add(rd['reference_name'])
            stats['missing_transcript'] += 1
            nh = next((v for t, v, _ in rd.get('tags', []) if t == 'NH'), None)
            missing_details.append({'transcript_id': rd['reference_name'],
                                     'flag': rd['flag'], 'nh_tag': nh})
            continue

        try:
            converted, warn = convert_read_coordinates(rd, tx)
            if warn: intron_warn[warn] += 1
            if converted:
                results.append(converted)
                stats['converted'] += 1
            else:
                stats['conversion_failed'] += 1
        except Exception:
            stats['conversion_failed'] += 1

    return results, dict(stats), missing_tx, dict(intron_warn), missing_details


def reverse_complement(seq):
    comp = str.maketrans('ACGTacgtNn', 'TGCAtgcaNn')
    return seq.translate(comp)[::-1]


def convert_read_coordinates(rd, tx):
    tx_start = rd.get('reference_start')
    warn = None

    if tx_start is None: return None, None

    # Always recompute tx_end from CIGAR, explicitly excluding N (op=3).
    # pysam's reference_end includes N in its calculation, which is wrong for
    # INDEGRA-style inputs where N represents genomic introns embedded inside a
    # transcript-space CIGAR.  Recomputing from cigartuples is equally correct
    # for standard STAR inputs (which have no N in the tx CIGAR), so there is
    # no downside to always doing this.
    if rd.get('cigartuples'):
        ref_cons = sum(l for op, l in rd['cigartuples'] if op in (0, 2, 7, 8))
        tx_end = tx_start + ref_cons if ref_cons else None
    else:
        tx_end = rd.get('reference_end')   # no CIGAR: fall back to stored value
    if tx_end is None: return None, None

    regions = tx.transcript_region_to_genome(tx_start, tx_end)
    if not regions: return None, None

    mapped_len  = sum(r[3] for r in regions)
    g_start, g_end = regions[0][1], regions[-1][2]
    span = g_end - g_start
    spans_intron = len(regions) > 1
    max_intron = 0

    for i in range(len(regions) - 1):
        isz = regions[i+1][1] - regions[i][2]
        if isz < 0: return None, None
        if isz > worker_max_intron_size: return None, f"intron_>{worker_max_intron_size}bp"
        if isz > worker_warn_intron_size: warn = f"large_intron_{isz//1000}kb"
        max_intron = max(max_intron, isz)

    # For minus-strand genes, the transcript CIGAR is in 5'→3' transcript order,
    # but _build_genome_cigar assigns ops to genomic regions in 3'→5' order
    # (leftmost region = 3' end of transcript = regions[0]).  After RC the stored
    # sequence also goes 3'→5'.  For pure-M CIGARs (Illumina) the two reversals
    # cancel automatically.  For complex CIGARs with many D/I operations (nanopore),
    # each D advances the reference without advancing the query, causing query bases
    # to be placed at progressively wrong genomic positions (up to 58 bp off in the
    # test read).  Reversing the non-clip CIGAR ops aligns their order with the
    # 3'→5' direction of both the genomic regions and the RC'd stored sequence.
    cigar_for_build = rd['cigartuples']
    if tx.strand == '-' and cigar_for_build:
        _CLIP = (4, 5)   # S=4, H=5
        mid = list(cigar_for_build)
        lead_c, trail_c = [], []
        while mid and mid[0][0] in _CLIP:
            lead_c.append(mid.pop(0))
        while mid and mid[-1][0] in _CLIP:
            trail_c.insert(0, mid.pop())
        cigar_for_build = lead_c + list(reversed(mid)) + trail_c

    cigar = _build_genome_cigar(cigar_for_build, regions)
    if not cigar: return None, None

    pm = tx.calculate_position_metrics(g_start, g_end)
    conv = {
        'query_name':     rd['query_name'],
        'query_sequence': rd['query_sequence'],
        'query_qualities':rd['query_qualities'],
        'flag':           rd['flag'],
        'reference_name': regions[0][0],
        'reference_start':regions[0][1],
        'cigartuples':    cigar,
        'mapping_quality':rd['mapping_quality'],
        'tags':           list(rd.get('tags', [])),
        'is_unmapped':    False,
        'is_paired':      rd.get('is_paired', False),
    }
    conv['tags'] += [
        ('tx', tx.transcript_id,  'Z'),
        ('gn', tx.gene_id,        'Z'),
        ('gs', g_start,           'i'),
        ('ge', g_end,             'i'),
        ('xl', mapped_len,        'i'),
        ('xp', span,              'i'),
        ('xi', int(spans_intron), 'i'),
        ('ds', pm['start_from_gene_start'], 'i'),
        ('de', pm['start_from_gene_end'],   'i'),
        ('es', pm['end_from_gene_start'],   'i'),
        ('ee', pm['end_from_gene_end'],     'i'),
        ('ro', -1 if (conv['flag'] & 16) else 1, 'i'),
    ]
    if max_intron > 0:
        conv['tags'].append(('im', max_intron, 'i'))

    if tx.strand == '-':
        conv['flag'] ^= 0x10
        # For minus-strand genes the read sequence must be reverse-complemented
        # and quality scores reversed so they remain consistent with the flipped
        # FLAG 0x10.  SAM convention: when FLAG 0x10 is set, SEQ stores
        # RC(original_read).  Flipping the flag without also flipping SEQ/quals
        # leaves every base mismatching the reference.
        if conv['query_qualities']:
            conv['query_qualities'] = conv['query_qualities'][::-1]
        if conv['query_sequence']:
            conv['query_sequence'] = reverse_complement(conv['query_sequence'])
        # After RC the read is 5'↔3' flipped in genomic space, so leading clips
        # (5'-transcript end = rightmost genomic position) must become trailing
        # clips and vice versa.  Without this swap, clip bases fall inside the
        # matched region and appear as spurious mismatches.
        # Each clip group is also internally reversed to preserve the SAM rule
        # that H must appear before S at each end.
        cigar = conv['cigartuples']
        if cigar:
            _CLIP = (4, 5)          # S=4, H=5
            i = 0
            while i < len(cigar) and cigar[i][0] in _CLIP:
                i += 1
            lead = list(cigar[:i])
            j = len(cigar) - 1
            while j >= i and cigar[j][0] in _CLIP:
                j -= 1
            trail = list(cigar[j+1:])
            middle = list(cigar[i:j+1])
            conv['cigartuples'] = list(reversed(trail)) + middle + list(reversed(lead))

    return conv, warn


def _build_genome_cigar(tx_cigar, regions):
    if not regions: return None
    M,I,D,N,S,H,P,EQ,X = 0,1,2,3,4,5,6,7,8
    new_cigar = []
    ridx = rconsume = 0

    for op, length in tx_cigar:
        if op in (S, H):
            new_cigar.append((op, length)); continue
        if op == I:
            new_cigar.append((op, length)); continue
        if op == N:
            # N in the tx CIGAR = intron/gap already present in the input
            # (e.g. from INDEGRA, which keeps genomic intron N ops in the
            # transcript-space BAM).  These do NOT consume transcript reference
            # and must NOT be passed through: the correct genomic N operations
            # are re-derived from the GTF exon model during region mapping.
            continue
        if op in (M, EQ, X, D):
            rem = length
            while rem > 0 and ridx < len(regions):
                reg = regions[ridx]
                rrm = reg[3] - rconsume
                if rrm <= 0:
                    ridx += 1; rconsume = 0
                    if ridx < len(regions):
                        isz = regions[ridx][1] - regions[ridx-1][2]
                        if isz > 0: new_cigar.append((N, isz))
                    continue
                consume = min(rem, rrm)
                new_cigar.append((op, consume))
                rem -= consume; rconsume += consume
                if rconsume >= reg[3]:
                    ridx += 1; rconsume = 0
                    # Always insert the intron N when crossing an exon boundary,
                    # even if rem==0 (op ended exactly on the boundary).
                    if ridx < len(regions):
                        isz = regions[ridx][1] - regions[ridx-1][2]
                        if isz > 0: new_cigar.append((N, isz))
        else:
            new_cigar.append((op, length))

    # merge adjacent same-op (but not N, EQ, X)
    preserve = worker_preserve_cigar_ops if 'worker_preserve_cigar_ops' in globals() else True
    merged = []
    for op, length in new_cigar:
        if merged and merged[-1][0] == op:
            if op == N: merged.append((op, length))
            elif preserve and op in (EQ, X): merged.append((op, length))
            else: merged[-1] = (op, merged[-1][1] + length)
        else:
            merged.append((op, length))
    return merged

# ---------------------------------------------------------------------------
# Producer / consumer workers
# ---------------------------------------------------------------------------

def _producer_process(task_q, input_bam, batch_size, n_workers):
    try:
        with pysam.AlignmentFile(input_bam, "rb", check_sq=False) as bam:
            batch, bid = [], 0
            for read in bam:
                batch.append(_serialize(read))
                if len(batch) >= batch_size:
                    task_q.put((batch, bid)); batch = []; bid += 1
            if batch: task_q.put((batch, bid))
    except Exception as e:
        logger.error(f"Producer error: {e}", exc_info=True)
    finally:
        for _ in range(n_workers): task_q.put(None)


def _consumer_worker(task_q, res_q, prog_q, worker_id, tmp_path, hdr_dict,
                     min_mapq, tx_data, tx_lookup, max_intron, warn_intron,
                     filt_sec, direct, preserve):
    init_worker(tx_data, tx_lookup, max_intron, warn_intron, filt_sec, direct, preserve)
    loc_stats = defaultdict(int)
    loc_miss = set(); loc_warn = Counter(); loc_miss_det = []
    hdr = pysam.AlignmentHeader.from_dict(hdr_dict)
    try:
        with pysam.AlignmentFile(tmp_path, "wb", header=hdr) as out:
            while True:
                task = task_q.get()
                if task is None: break
                batch_reads, bid = task
                res = process_read_batch((batch_reads, min_mapq, bid))
                conv, b_stats, b_miss, b_warn, b_miss_det = res
                for k, v in b_stats.items(): loc_stats[k] += v
                loc_miss.update(b_miss)
                for w, c in b_warn.items(): loc_warn[w] += c
                loc_miss_det.extend(b_miss_det)
                if TQDM_AVAILABLE: prog_q.put(b_stats.get('total', 0))
                for rd in conv: out.write(_deserialize(rd, hdr))
    except Exception as e:
        logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
        loc_stats['error'] += 1
    finally:
        res_q.put((dict(loc_stats), loc_miss, dict(loc_warn), loc_miss_det))


# Tags that could not be written are reported once per tag name.  Workers are
# separate processes, so this is warn-once-per-tag-per-worker, not global.
_TAG_DROP_WARNED = set()


def _serialize(read):
    tags = []
    try:
        tags = [(t, v, tp) for t, v, tp in read.get_tags(with_value_type=True)]
    except Exception:
        tags = read.get_tags()
    ref_end = None
    if not read.is_unmapped:
        try: ref_end = read.reference_end
        except Exception: pass
    return dict(
        query_name      = read.query_name,
        query_sequence  = read.query_sequence,
        query_qualities = read.query_qualities.tolist() if read.query_qualities is not None else None,
        flag            = read.flag,
        reference_name  = read.reference_name,
        reference_start = read.reference_start,
        reference_end   = ref_end,
        mapping_quality = read.mapping_quality,
        cigartuples     = read.cigartuples,
        tags            = tags,
        is_unmapped     = read.is_unmapped,
        is_paired       = read.is_paired,
    )


def _deserialize(d, hdr):
    r = pysam.AlignedSegment(hdr)
    r.query_name     = d['query_name']
    r.query_sequence = d['query_sequence']
    if d['query_qualities']: r.query_qualities = d['query_qualities']
    r.flag = d['flag']
    if not d['is_unmapped'] and d.get('reference_name'):
        r.reference_name  = d['reference_name']
        r.reference_start = d['reference_start']
        if d.get('cigartuples'): r.cigartuples = d['cigartuples']
    r.mapping_quality = d['mapping_quality']
    for tup in d.get('tags', []):
        try:
            # pysam reports array-valued tags with the container type code 'B',
            # but set_tag rejects 'B' -- it needs the element type, which it can
            # infer from the array.array typecode when no code is passed.  Any
            # explicit 'B' here raises, which is how ML and pa were being lost.
            if len(tup) == 3 and tup[2] != 'B':
                r.set_tag(tup[0], tup[1], tup[2])
            else:
                r.set_tag(tup[0], tup[1])
        except Exception as e:
            if tup[0] not in _TAG_DROP_WARNED:
                _TAG_DROP_WARNED.add(tup[0])
                logger.warning("tag %s could not be written and is being "
                               "dropped: %s", tup[0], e)
    return r

# ---------------------------------------------------------------------------
# ParallelConverter — main orchestrator
# ---------------------------------------------------------------------------

class ParallelConverter:

    def __init__(self, gtf_parser, threads=1, batch_size=500, min_mapq=0,
                 max_intron_size=500_000, warn_intron_size=100_000,
                 chrom_sizes=None, low_memory=False, parallel_write=False,
                 filter_secondary=False, direct=False, preserve_cigar_ops=True,
                 validate_mode=False, pair_config=None):
        self.gtf_parser       = gtf_parser
        self.threads          = threads
        self.batch_size       = batch_size
        self.min_mapq         = min_mapq
        self.max_intron_size  = max_intron_size
        self.warn_intron_size = warn_intron_size
        self.chrom_sizes      = chrom_sizes or ChromosomeSizes()
        self.parallel_write   = parallel_write
        self.filter_secondary = filter_secondary
        self.direct           = direct
        self.preserve_cigar_ops = preserve_cigar_ops
        self.validate_mode    = validate_mode
        self.pair_config      = pair_config

    # ---------------------------------------------------------------- public API

    def convert_bam(self, input_bam, output_bam, sort_output=True):
        logger.info(f"Converting {input_bam} → {output_bam}")
        logger.info(f"Threads: {self.threads},  batch size: {self.batch_size}")
        if self.pair_config and self.pair_config.enabled:
            mode = "cross-transcript" if self.pair_config.cross_transcript else "same-transcript"
            logger.info(f"Pair restoration: ON  ({mode})")
        else:
            logger.info("Pair restoration: OFF")
        if self.parallel_write:
            return self._run_producer_consumer(input_bam, output_bam, sort_output)
        return self._run_streaming(input_bam, output_bam, sort_output)

    # ---------------------------------------------------------------- internals

    def _prep_worker_data(self):
        logger.info(f"Serialising {len(self.gtf_parser.transcripts)} transcripts for workers …")
        tx_data, tx_lookup = {}, {}
        for tid, tx in self.gtf_parser.transcripts.items():
            tx_data[tid] = dict(transcript_id=tx.transcript_id, gene_id=tx.gene_id,
                                chrom=tx.chrom, strand=tx.strand, exons=tx.exons,
                                gene_start=tx.gene_start, gene_end=tx.gene_end)
            tx_lookup[tid] = tid
            tx_lookup[tid.split('.')[0]] = tid
        return tx_data, tx_lookup

    def _create_header(self, old_hdr):
        d = old_hdr.to_dict()
        chrom_maxpos = defaultdict(int)
        for tx in self.gtf_parser.transcripts.values():
            for ex in tx.exons:
                chrom_maxpos[ex.chrom] = max(chrom_maxpos[ex.chrom], ex.end)
        d['SQ'] = [{'SN': c,
                    'LN': self.chrom_sizes.get_size(c) if self.chrom_sizes.sizes
                          else chrom_maxpos[c] + 1_000_000}
                   for c in sorted(chrom_maxpos)]
        d.setdefault('PG', []).append({'ID': 't2g_converter',
                                        'PN': 'transcriptome_to_genome_converter',
                                        'VN': '5.7', 'CL': ' '.join(sys.argv)})
        return pysam.AlignmentHeader.from_dict(d)

    def _run_pair_restoration(self, bam_path):
        if not (self.pair_config and self.pair_config.enabled): return {}
        logger.info("Running pair restoration pass …")
        tmp = bam_path + ".pairing_tmp.bam"
        stats = PairRestorator(self.pair_config).restore_pairs(bam_path, tmp)
        os.replace(tmp, bam_path)
        return stats

    def _report_pair_stats(self, ps):
        if not ps: return
        logger.info("\nPair restoration results:")
        logger.info(f"  Total reads scanned       : {ps.get('total',0):,}")
        logger.info(f"  Pass-through (no XT/unpaired): {ps.get('passthrough',0):,}")
        logger.info(f"  Same-transcript pairs     : {ps.get('same_tx_pairs',0):,}  "
                    f"({ps.get('same_tx_pairs',0)*2:,} reads)")
        if self.pair_config and self.pair_config.cross_transcript:
            logger.info(f"  Cross-transcript pairs    : {ps.get('cross_tx_pairs',0):,}  "
                        f"({ps.get('cross_tx_pairs',0)*2:,} reads)")
        logger.info(f"  Singletons                : {ps.get('singletons',0):,}")
        if ps.get('ambiguous'):
            logger.info(f"  Ambiguous (>2/key)        : {ps['ambiguous']:,}")

    @staticmethod
    def _monitor(pbar, pq, stop_ev):
        while not stop_ev.is_set():
            try:
                n = pq.get(timeout=0.1)
                if n: pbar.update(n)
            except queue.Empty: pass
            except (IOError, EOFError): break
        while not pq.empty():
            try:
                n = pq.get_nowait()
                if n: pbar.update(n)
            except queue.Empty: break

    def _run_producer_consumer(self, input_bam, output_bam, sort_output):
        start = time.time()
        with pysam.AlignmentFile(input_bam, "rb") as bam:
            new_hdr = self._create_header(bam.header)
            total = None
            if TQDM_AVAILABLE:
                try: total = bam.count()
                except Exception: pass

        tx_data, tx_lookup = self._prep_worker_data()
        task_q = mp.Queue(maxsize=self.threads * 4)
        res_q  = mp.Queue()
        prog_q = mp.Queue()
        tmp_dir = tempfile.mkdtemp(prefix="t2g_")

        producer = mp.Process(target=_producer_process,
                              args=(task_q, input_bam, self.batch_size, self.threads))
        producer.start()
        consumers = []
        for i in range(self.threads):
            tmp_bam = os.path.join(tmp_dir, f"w{i}.bam")
            p = mp.Process(target=_consumer_worker,
                           args=(task_q, res_q, prog_q, i, tmp_bam, new_hdr.to_dict(),
                                 self.min_mapq, tx_data, tx_lookup, self.max_intron_size,
                                 self.warn_intron_size, self.filter_secondary,
                                 self.direct, self.preserve_cigar_ops))
            p.start(); consumers.append(p)

        pbar = mon_thread = None
        stop_ev = threading.Event()
        if TQDM_AVAILABLE:
            pbar = tqdm(total=total, desc="Converting reads", unit=" reads")
            mon_thread = threading.Thread(target=self._monitor, args=(pbar, prog_q, stop_ev))
            mon_thread.start()

        g_stats = defaultdict(int); g_miss = set()
        g_warn = Counter(); miss_stats = MissingTranscriptStats()
        for _ in range(self.threads):
            ws, wm, ww, wmd = res_q.get()
            for k, v in ws.items(): g_stats[k] += v
            g_miss.update(wm)
            for w, c in ww.items(): g_warn[w] += c
            for d in wmd: miss_stats.add_read(d['transcript_id'], d['flag'], d.get('nh_tag'))

        producer.join()
        for p in consumers: p.join()
        if mon_thread: stop_ev.set(); mon_thread.join()
        if pbar: pbar.close()

        logger.info("Merging worker BAMs …")
        tmp_files = [f for f in [os.path.join(tmp_dir, f"w{i}.bam")
                                  for i in range(self.threads)]
                     if os.path.exists(f) and os.path.getsize(f) > 0]
        if tmp_files:
            pysam.merge("-f", output_bam, *tmp_files)
        else:
            logger.warning("All worker outputs empty — writing empty BAM")
            with pysam.AlignmentFile(output_bam, "wb", header=new_hdr): pass
        shutil.rmtree(tmp_dir, ignore_errors=True)

        pair_stats = self._run_pair_restoration(output_bam)

        if sort_output and os.path.getsize(output_bam) > 0:
            logger.info("Sorting …")
            tmp_s = output_bam + ".sort.bam"
            pysam.sort("-@", str(self.threads), "-o", tmp_s, output_bam)
            os.replace(tmp_s, output_bam)
        if os.path.getsize(output_bam) > 0:
            pysam.index(output_bam)

        self._report_stats(g_stats, g_miss, g_warn, miss_stats, start)
        self._report_pair_stats(pair_stats)

    def _run_streaming(self, input_bam, output_bam, sort_output):
        start = time.time()
        tmp_dir = os.path.dirname(output_bam) or tempfile.gettempdir()
        fd, tmp_bam = tempfile.mkstemp(suffix='.bam', dir=tmp_dir)
        os.close(fd)

        tx_data, tx_lookup = self._prep_worker_data()
        with pysam.AlignmentFile(input_bam, "rb") as bam:
            new_hdr = self._create_header(bam.header)
            total = None
            if TQDM_AVAILABLE:
                try: total = bam.count()
                except Exception: pass

        stats = defaultdict(int); g_miss = set()
        g_warn = Counter(); miss_stats = MissingTranscriptStats()

        with pysam.AlignmentFile(tmp_bam, "wb", header=new_hdr) as out:
            with mp.Pool(processes=self.threads, initializer=init_worker,
                         initargs=(tx_data, tx_lookup, self.max_intron_size,
                                   self.warn_intron_size, self.filter_secondary,
                                   self.direct, self.preserve_cigar_ops)) as pool:
                pbar = tqdm(total=total, desc="Converting", unit=" reads") if TQDM_AVAILABLE and total else None
                try:
                    for res in pool.imap_unordered(process_read_batch,
                                                   self._batches(input_bam)):
                        conv, bs, bm, bw, bmd = res
                        for k, v in bs.items(): stats[k] += v
                        g_miss.update(bm)
                        for w, c in bw.items(): g_warn[w] += c
                        for d in bmd: miss_stats.add_read(d['transcript_id'], d['flag'], d.get('nh_tag'))
                        for rd in conv: out.write(_deserialize(rd, out.header))
                        if pbar: pbar.update(bs.get('total', 0))
                finally:
                    if pbar: pbar.close()

        pair_stats = self._run_pair_restoration(tmp_bam)

        logger.info("Sorting …")
        pysam.sort("-@", str(self.threads), "-o", output_bam, tmp_bam)
        os.remove(tmp_bam)
        pysam.index(output_bam)

        self._report_stats(stats, g_miss, g_warn, miss_stats, start)
        self._report_pair_stats(pair_stats)

    def _batches(self, input_bam):
        with pysam.AlignmentFile(input_bam, "rb") as bam:
            batch, bid = [], 0
            for read in bam:
                batch.append(_serialize(read))
                if len(batch) >= self.batch_size:
                    yield (batch, self.min_mapq, bid); batch = []; bid += 1
            if batch: yield (batch, self.min_mapq, bid)

    def _report_stats(self, stats, missing, intron_warn, miss_stats, start):
        elapsed = time.time() - start
        tot = stats.get('total', 0)
        logger.info(f"\nConversion complete in {elapsed:.1f}s")
        logger.info(f"  Total reads     : {tot:,}")
        logger.info(f"  Converted       : {stats.get('converted',0):,}")
        logger.info(f"  Unmapped        : {stats.get('unmapped',0):,}")
        logger.info(f"  Missing tx      : {stats.get('missing_transcript',0):,}")
        logger.info(f"  Conv. failed    : {stats.get('conversion_failed',0):,}")
        logger.info(f"  Low MAPQ skip   : {stats.get('low_mapq_skipped',0):,}")
        if self.filter_secondary:
            logger.info(f"  Secondary filt  : {stats.get('secondary_filtered',0):,}")
        if elapsed > 0 and tot > 0:
            logger.info(f"  Reads/sec       : {tot/elapsed:.0f}")
        if miss_stats.total_reads > 0:
            logger.info(miss_stats.report())
        if intron_warn:
            logger.info("Intron size warnings:")
            for w, c in intron_warn.most_common(10):
                logger.info(f"  {w}: {c:,}")

# ---------------------------------------------------------------------------
# Batch conversion helper
# ---------------------------------------------------------------------------

def batch_convert_directory(gtf_parser, input_dir, output_subdir="t2g_output",
                             sort_output=True, verbose=False, **kw):
    bam_files = glob.glob(os.path.join(input_dir, "*.bam"))
    if not bam_files:
        logger.error(f"No BAM files in {input_dir}"); return
    logger.info(f"Found {len(bam_files)} BAM files")
    out_dir = os.path.join(input_dir, output_subdir)
    os.makedirs(out_dir, exist_ok=True)
    for i, ib in enumerate(sorted(bam_files)):
        ob = os.path.join(out_dir, os.path.basename(ib).replace('.bam', '_t2g.bam'))
        logger.info(f"[{i+1}/{len(bam_files)}] {os.path.basename(ib)}")
        if os.path.exists(ob) and os.path.exists(ob + '.bai'):
            logger.info("  Already exists, skipping"); continue
        try:
            ParallelConverter(gtf_parser=gtf_parser, **kw).convert_bam(ib, ob, sort_output)
        except Exception as e:
            logger.error(f"  Failed: {e}")
            if verbose:
                import traceback; traceback.print_exc()
    logger.info(f"Batch done. Output in: {out_dir}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_default_threads():
    n = mp.cpu_count()
    return max(1, n - 1) if n <= 4 else n - 2


def validate_files(args):
    if not os.path.exists(args.gtf):
        raise FileNotFoundError(f"GTF not found: {args.gtf}")
    if hasattr(args, 'directory') and args.directory:
        if not os.path.isdir(args.directory):
            raise ValueError(f"Not a directory: {args.directory}")
    elif args.input_bam:
        if not os.path.exists(args.input_bam):
            raise FileNotFoundError(f"BAM not found: {args.input_bam}")
        out_dir = os.path.dirname(args.output_bam)
        if out_dir: os.makedirs(out_dir, exist_ok=True)
    if args.chrom_sizes and not os.path.exists(args.chrom_sizes):
        raise FileNotFoundError(f"Chrom sizes not found: {args.chrom_sizes}")


def main():
    p = argparse.ArgumentParser(
        description='Transcriptome-to-genome BAM converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
# Paired-end, single file (pair restoration on by default)
  %(prog)s -g annotation.gtf -i tx.bam -o genome.bam

# With cross-transcript pairing (handles discordant mates / multimappers)
  %(prog)s -g annotation.gtf -i tx.bam -o genome.bam --cross-transcript-pairs

# Save singletons and a pairing summary
  %(prog)s -g annotation.gtf -i tx.bam -o genome.bam \\
      --unpaired-bam singletons.bam --pair-summary pairs.tsv

# Single-end data (skip pair restoration)
  %(prog)s -g annotation.gtf -i tx.bam -o genome.bam --no-pair-restore

# Parallel write mode (best throughput)
  %(prog)s -g annotation.gtf -i tx.bam -o genome.bam --parallel-write -t 8

# Batch conversion of a directory
  %(prog)s -g annotation.gtf -d /path/to/bams --cross-transcript-pairs

Tags written (lowercase = SAM-spec reserved for user apps, no conflicts)
------------
  tx  transcript ID
  gn  gene ID
  gs  genome 5' start (used for PNEXT)
  ge  genome 3' end
  xl  mapped length (exons only, bp)
  xp  mapped span (including introns, bp; used for TLEN)
  xi  spans-intron flag (1=yes, 0=no)
  im  maximum intron size in the read
  ro  read orientation (1=direct, -1=reverse complement)
  pk  pair class (0=singleton, 1=same-transcript, 2=cross-transcript)
  ds  5'-end distance from gene start
  de  5'-end distance from gene end
  es  3'-end distance from gene start
  ee  3'-end distance from gene end

Multimapper pairing
-------------------
  Uses the HI (hit-index) tag to pair each alignment of a multimapper with its
  correct mate.  R1-HI=2 is paired with R2-HI=2, etc., even if they mapped to
  different transcripts (requires --cross-transcript-pairs).
        """)

    p.add_argument('-g','--gtf', required=True)
    inp = p.add_mutually_exclusive_group(required=True)
    inp.add_argument('-i','--input-bam')
    inp.add_argument('-d','--directory')
    p.add_argument('-o','--output-bam')
    p.add_argument('--output-subdir', default='t2g_output')
    p.add_argument('-t','--threads', type=int, default=get_default_threads())
    p.add_argument('--batch-size', type=int, default=500)
    p.add_argument('--min-mapq', type=int, default=0)
    ig = p.add_mutually_exclusive_group()
    ig.add_argument('--species', choices=list(SPECIES_INTRON_SIZES))
    ig.add_argument('--max-intron', type=int, default=500_000)
    p.add_argument('--warn-intron', type=int, default=100_000)
    p.add_argument('--chrom-sizes')
    p.add_argument('--strip-version', action='store_true')
    p.add_argument('--no-sort', action='store_true')
    p.add_argument('--parallel-write', action='store_true')
    p.add_argument('--primary-only', action='store_true')
    p.add_argument('--direct-only', action='store_true')
    p.add_argument('--no-preserve-cigar', action='store_true')
    p.add_argument('--validate', action='store_true')

    pg = p.add_argument_group('Pair restoration')
    pg.add_argument('--no-pair-restore', action='store_true',
                    help='Disable pair restoration (use for single-end data)')
    pg.add_argument('--cross-transcript-pairs', action='store_true',
                    help='Pair mates that mapped to different transcripts (uses HI tag)')
    pg.add_argument('--unpaired-bam', default=None,
                    help='Write singletons here instead of main output')
    pg.add_argument('--ambiguous-bam', default=None,
                    help='Write ambiguous reads (>2 per key) here')
    pg.add_argument('--pair-summary', default=None,
                    help='TSV file with one row per restored pair')

    p.add_argument('-v','--verbose', action='store_true')
    p.add_argument('--version', action='version', version='%(prog)s 5.7')

    args = p.parse_args()

    if args.input_bam and not args.output_bam:
        p.error("-o required with -i")
    if args.directory and args.output_bam:
        p.error("-o cannot be used with -d")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s  %(levelname)s  %(message)s',
        datefmt='%H:%M:%S')

    logger.info("t2g BAM converter v5.7")
    logger.info(f"CPU cores: {mp.cpu_count()},  threads: {args.threads}")

    if args.species:
        max_intron = SPECIES_INTRON_SIZES[args.species]
        if max_intron is None:
            p.error("--species custom requires --max-intron")
    else:
        max_intron = args.max_intron

    try:
        if sys.platform == 'darwin' and mp.get_start_method(allow_none=True) != 'fork':
            mp.set_start_method('fork', force=True)

        validate_files(args)
        chrom_sizes = ChromosomeSizes(args.chrom_sizes) if args.chrom_sizes else None
        gtf = GTFParser(args.gtf, threads=args.threads, strip_version=args.strip_version)

        pair_cfg = PairRestorationConfig(
            enabled          = not args.no_pair_restore,
            cross_transcript = args.cross_transcript_pairs,
            unpaired_output  = args.unpaired_bam,
            ambiguous_output = args.ambiguous_bam,
            summary          = args.pair_summary,
        )

        kw = dict(threads=args.threads, batch_size=args.batch_size,
                  min_mapq=args.min_mapq, max_intron_size=max_intron,
                  warn_intron_size=args.warn_intron, chrom_sizes=chrom_sizes,
                  parallel_write=args.parallel_write,
                  filter_secondary=args.primary_only, direct=args.direct_only,
                  preserve_cigar_ops=not args.no_preserve_cigar,
                  validate_mode=args.validate, pair_config=pair_cfg)

        if args.directory:
            batch_convert_directory(gtf, args.directory,
                                    output_subdir=args.output_subdir,
                                    sort_output=not args.no_sort,
                                    verbose=args.verbose, **kw)
        else:
            ParallelConverter(gtf_parser=gtf, **kw).convert_bam(
                args.input_bam, args.output_bam, sort_output=not args.no_sort)

        logger.info("Done.")

    except KeyboardInterrupt:
        logger.error("Interrupted"); sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal: {e}")
        if args.verbose:
            import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
