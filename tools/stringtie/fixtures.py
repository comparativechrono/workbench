#!/usr/bin/env python3
"""Deterministic, synthetic-only StringTie truth; no aligner or quantifier used.

BAM is written directly from SAM/BAM 1.6 structures using Python's standard
library. Coordinates inside this module are zero-based, half-open; GTF writes
one-based, closed coordinates. BAM SEQ is the reference-oriented aligned read.
"""
from pathlib import Path
import json
import random
import struct
import zlib


REFERENCE_NAME = 'chrSynthetic'
REFERENCE_LENGTH = 5000
TRANSCRIPTS = (
    {'gene': 'gene_plus', 'transcript': 'tx_plus', 'strand': '+',
     'exons': [(100, 350), (450, 700)], 'copies': 1},
    {'gene': 'gene_minus', 'transcript': 'tx_minus', 'strand': '-',
     'exons': [(1500, 1750), (1850, 2100)], 'copies': 2},
    {'gene': 'gene_unexpressed', 'transcript': 'tx_unexpressed', 'strand': '+',
     'exons': [(3000, 3250), (3350, 3600)], 'copies': 0},
)
BGZF_EOF = bytes.fromhex('1f8b08040000000000ff0600424302001b0003000000000000000000')


def reverse_complement(sequence):
    return sequence.translate(str.maketrans('ACGT', 'TGCA'))[::-1]


def reference_sequence():
    rng = random.Random(20261013)
    sequence = list(''.join(rng.choice('ACGT') for _ in range(REFERENCE_LENGTH)))
    # Canonical GT/AG on the forward strand and CT/AC on the reverse strand.
    for tx in TRANSCRIPTS:
        left, right = tx['exons'][0][1], tx['exons'][1][0]
        sequence[left:left + 2] = 'GT' if tx['strand'] == '+' else 'CT'
        sequence[right - 2:right] = 'AG' if tx['strand'] == '+' else 'AC'
    return ''.join(sequence)


def _reg2bin(begin, end):
    end -= 1
    for shift, offset in ((14, 4681), (17, 585), (20, 73), (23, 9), (26, 1)):
        if begin >> shift == end >> shift:
            return offset + (begin >> shift)
    return 0


def _bgzf(data):
    # A stored DEFLATE block is byte-identical across Python/zlib versions.
    # The fixtures are tiny; deterministic truth is more useful than compression.
    if len(data) > 65535:
        raise ValueError('Stored BGZF block data exceeds 65535 bytes')
    payload = b'\x01' + struct.pack('<HH', len(data), 65535 - len(data)) + data
    block = (b'\x1f\x8b\x08\x04' + bytes(4) + b'\x00\xff\x06\x00BC\x02\x00'
             + struct.pack('<H', len(payload) + 25) + payload
             + struct.pack('<II', zlib.crc32(data), len(data)))
    if len(block) > 65536:
        raise ValueError('BGZF block exceeds 64 KiB')
    return block


def bam_bytes(rows, references=((REFERENCE_NAME, REFERENCE_LENGTH),), sort='coordinate'):
    """Encode rows with name, flag, pos, cigar, sequence and strand fields.

    Optional mate_pos/tlen/ref_id/mate_ref support scientifically explicit paired
    or multireference negative fixtures without reliance on external tools.
    Deliberately does not sort: callers can construct actual out-of-order cases.
    """
    header = ('@HD\tVN:1.6\tSO:' + sort + '\n' + ''.join(
        '@SQ\tSN:' + name + '\tLN:' + str(length) + '\n'
        for name, length in references)).encode('ascii')
    body = bytearray(b'BAM\1' + struct.pack('<i', len(header)) + header
                     + struct.pack('<i', len(references)))
    for name, length in references:
        encoded = name.encode('ascii') + b'\0'
        body += struct.pack('<i', len(encoded)) + encoded + struct.pack('<i', length)
    codes = '=ACMGRSVTWYHKDBN'
    for row in rows:
        name = row['name'].encode('ascii') + b'\0'
        cigar = row['cigar']
        sequence = row['sequence']
        assert sum(length for length, op in cigar if op in 'MIS=X') == len(sequence)
        assert len(name) <= 255
        end = row['pos'] + sum(length for length, op in cigar if op in 'MDN=X')
        ops = b''.join(struct.pack('<I', (length << 4) | 'MIDNSHP=XB'.index(op))
                       for length, op in cigar)
        packed = bytes((codes.index(sequence[i]) << 4) |
                       (codes.index(sequence[i + 1]) if i + 1 < len(sequence) else 0)
                       for i in range(0, len(sequence), 2))
        core = struct.pack('<iiIIiiii', row.get('ref_id', 0), row['pos'],
                           (_reg2bin(row['pos'], end) << 16) | (60 << 8) | len(name),
                           (row['flag'] << 16) | len(cigar), len(sequence),
                           row.get('mate_ref', -1), row.get('mate_pos', -1), row.get('tlen', 0))
        tags = b'NHi' + struct.pack('<i', 1) + b'NM' + b'i' + struct.pack('<i', 0)
        if row.get('strand'):
            tags += b'XSA' + row['strand'].encode('ascii')
        record = core + name + ops + packed + bytes([40]) * len(sequence) + tags
        body += struct.pack('<i', len(record)) + record
    return b''.join(_bgzf(body[i:i + 60000]) for i in range(0, len(body), 60000)) + BGZF_EOF


def alignment_rows():
    sequence = reference_sequence()
    rows = []
    for tx in TRANSCRIPTS:
        exonic_coordinates = [position for begin, end in tx['exons'] for position in range(begin, end)]
        # Tile in genomic order for both strands. For minus-strand reads the
        # sequenced original is the reverse complement of stored BAM SEQ.
        for copy in range(tx['copies']):
            for offset in range(0, len(exonic_coordinates) - 100 + 1, 10):
                coordinates = exonic_coordinates[offset:offset + 100]
                cigar = []
                run = 1
                for previous, current in zip(coordinates, coordinates[1:]):
                    if current == previous + 1:
                        run += 1
                    else:
                        cigar.extend([(run, 'M'), (current - previous - 1, 'N')])
                        run = 1
                cigar.append((run, 'M'))
                rows.append({'name': tx['transcript'] + '_' + str(copy) + '_' + str(offset),
                             'flag': 0 if tx['strand'] == '+' else 16,
                             'pos': coordinates[0], 'cigar': cigar,
                             'sequence': ''.join(sequence[position] for position in coordinates),
                             'strand': tx['strand']})
    return sorted(rows, key=lambda row: (row['pos'], row['name']))


def gtf_text(transcripts=TRANSCRIPTS, reference=REFERENCE_NAME):
    rows = []
    for tx in transcripts:
        attributes = 'gene_id "' + tx['gene'] + '"; transcript_id "' + tx['transcript'] + '";'
        for begin, end in tx['exons']:
            rows.append('\t'.join((reference, 'synthetic_truth', 'exon', str(begin + 1), str(end),
                                   '.', tx['strand'], '.', attributes)))
    return '\n'.join(rows) + '\n'


def integration_files():
    """Same genome and loci as the accepted HISAT2 fixture; distinct read names.

    Independent construction, not a call to HISAT2's fixture implementation.
    Twelve pairs are biological duplicate molecules with unique names and no
    duplicate marking; expected pair positions and CIGARs are fixed by slicing.
    """
    rng = random.Random(20261003)
    sequence = ''.join(rng.choice('ACGT') for _ in range(1100))
    sequence = sequence[:500] + 'GT' + sequence[502:598] + 'AG' + sequence[600:]
    reads1 = sequence[470:500] + sequence[600:630]
    reads2 = reverse_complement(sequence[690:750])
    def fastq(sequence, mate):
        return ''.join('@rna_pair_' + str(i).zfill(3) + '/' + str(mate) + '\n' + sequence +
                       '\n+\n' + 'I' * len(sequence) + '\n' for i in range(1, 13))
    guide = ({'gene': 'integration_gene', 'transcript': 'integration_tx', 'strand': '+',
              'exons': [(470, 500), (600, 750)]},)
    return {'hisat-reference.fa': '>' + REFERENCE_NAME + '\n' + sequence + '\n',
            'hisat-r1.fastq': fastq(reads1, 1), 'hisat-r2.fastq': fastq(reads2, 2),
            'hisat-annotation.gtf': gtf_text(guide)}


def fixtures(directory):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    rows = alignment_rows()
    (out / 'spliced.bam').write_bytes(bam_bytes(rows))
    (out / 'empty.bam').write_bytes(bam_bytes([]))
    (out / 'guide.gtf').write_bytes(gtf_text().encode('ascii'))
    for name, content in integration_files().items():
        (out / name).write_bytes(content.encode('ascii'))
    total_aligned = sum(len(row['sequence']) for row in rows)
    truth = {
        'schema': 1, 'synthetic': True,
        'construction': 'Direct SAM/BAM 1.6 encoding, coordinate-sorted, MAPQ60, NM:i:0, NH:i:1, XS:A:+/-. Random DNA uses Python Random(20261013); canonical introns are planted. Two disjoint equal-length transcripts have dense 100-nt reads beginning at exonic offsets 0..400 in steps of 10. Minus transcript has two independent name sets; a third annotated transcript deliberately has no reads. Truth predates StringTie execution.',
        'coordinates': 'exons0 are zero-based half-open; GTF is one-based closed',
        'reference': {'name': REFERENCE_NAME, 'length': REFERENCE_LENGTH},
        'alignmentRecords': len(rows), 'alignedBases': total_aligned,
        'readLength': 100, 'pairing': 'single',
        'transcripts': [{'id': tx['transcript'], 'gene': tx['gene'], 'strand': tx['strand'],
                         'exons0': tx['exons'], 'length': 500, 'alignedReads': 41 * tx['copies'],
                         'splicedReads': 9 * tx['copies'], 'alignedBases': 4100 * tx['copies'],
                         'meanAlignedBaseCoverage': 8.2 * tx['copies'],
                         'idealEqualLengthTpm': 1000000 * tx['copies'] / 3}
                        for tx in TRANSCRIPTS],
        'interpretation': 'Coverage is exact input aligned-base arithmetic. Equal-length unambiguous expression ratio is 1:2, hence ideal TPM one third/two thirds. StringTie outputs are estimates and formatting/algorithm tolerances must be stated in assertions; no arbitrary biological pass threshold is implied.',
        'empty': {'alignmentRecords': 0, 'expectedExpression': 0,
                  'note': 'Header-only BAM has the same declared reference; zero expression is a successful no-evidence result.'},
        'integration': {
            'construction': 'Python Random(20261003) recreates the accepted HISAT2 synthetic genome; 12 uniquely named copies of the fixed pair, no aligner used to derive expected coordinates.',
            'reference': {'name': REFERENCE_NAME, 'length': 1100},
            'pairs': 12, 'records': 24, 'transcriptLength': 180,
            'transcript': 'integration_tx', 'gene': 'integration_gene',
            'exons0': [[470, 500], [600, 750]], 'strand': '+',
            'requiredMinimumTranscriptLength': 100,
            'expectedAlignments': [{'mate': 1, 'position1': 471, 'cigar': '30M100N30M', 'flag': 99},
                                   {'mate': 2, 'position1': 691, 'cigar': '60M', 'flag': 147}],
            'inputAlignedBases': 1440, 'meanAlignedBaseCoverage': 8,
            'idealSingleTranscriptTpm': 1000000,
            'note': 'An uncovered internal 60-nt interval is retained by reference-only estimation; this is not evidence for full transcript reconstruction from those reads alone.'}}
    (out / 'truth.json').write_bytes((json.dumps(truth, indent=2) + '\n').encode('ascii'))


if __name__ == '__main__':
    fixtures(Path(__file__).parent / 'fixtures')
