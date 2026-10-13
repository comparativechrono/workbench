#!/usr/bin/env python3
"""Independent synthetic BUS records: no kallisto index, FASTQ or biological claim."""
import json
from pathlib import Path
import struct

TRANSCRIPTS = ['txA1', 'txA2', 'txB', 'txC']
GENES = ['geneA', 'geneA', 'geneB', 'geneC']
ECS = [[0], [1], [2], [0, 1], [0, 2], [3]]
ALLOWLIST = ['AAAA', 'AACC', 'CCCC', 'TTTT']
# Deliberately unsorted; multiplicity is read support, not molecule count.
RECORDS = [('TTTT','AAAA',4,1), ('AAAA','AAAC',3,1), ('CCCA','AAAA',2,4),
           ('AAAA','AAAA',0,3), ('AAAC','AAAA',0,2), ('AAAA','AAAG',4,1),
           ('AAAA','AAAT',4,1), ('CCCC','AAAC',5,1), ('AAAA','AACA',0,1),
           ('AAAA','AAAA',0,2), ('AAAA','AAAC',1,2), ('GGGG','AAAA',2,3),
           ('AAAA','AAAG',0,1), ('AAAA','AACA',2,1)]
TRUTH = {'matrix': {'AAAA': {'geneA': 3}, 'CCCC': {'geneB': 1, 'geneC': 1}, 'TTTT': {}},
         'inputRecords': 14, 'inputReadMultiplicity': 24, 'retainedRecords': 12,
         'retainedReadMultiplicity': 19, 'countedMolecules': 5, 'barcodes': 3,
         'genes': 3, 'nonzeroEntries': 3,
         'explanation': 'AAAA has three uniquely resolved exact-UMI groups; multi-gene and empty intersections are discarded. CCCA corrects uniquely to CCCC; AAAC has two Hamming-1 targets and GGGG has none, so both are discarded. TTTT remains as a zero-count barcode row; rows are not called cells.'}

def encode(sequence):
    value = 0
    for char in sequence:
        value = (value << 2) | 'ACGT'.index(char)
    return value

def bus_bytes(records=RECORDS, barcode_length=4, umi_length=4):
    comment = b'Native Workbench independent synthetic BUS fixture'
    return (b'BUS\0' + struct.pack('<IIII', 1, barcode_length, umi_length, len(comment)) + comment +
            b''.join(struct.pack('<QQiIII', encode(bc), encode(umi), ec, count, 0, 0) for bc, umi, ec, count in records))

def build_fixture(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    files = {'bus': directory / 'synthetic.bus', 'transcripts': directory / 'transcripts.txt',
             'equivalence-classes': directory / 'matrix.ec', 'genes': directory / 'transcripts-to-genes.tsv',
             'allowlist': directory / 'allowlist.txt'}
    files['bus'].write_bytes(bus_bytes())
    files['transcripts'].write_text('\n'.join(TRANSCRIPTS) + '\n')
    files['equivalence-classes'].write_text(''.join(str(i) + '\t' + ','.join(map(str, row)) + '\n' for i, row in enumerate(ECS)))
    files['genes'].write_text(''.join(tx + '\t' + gene + '\n' for tx, gene in zip(TRANSCRIPTS, GENES)))
    files['allowlist'].write_text('\n'.join(ALLOWLIST) + '\n')
    (directory / 'expected.json').write_text(json.dumps(TRUTH, indent=2) + '\n')
    return files

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    build_fixture(parser.parse_args().directory)
