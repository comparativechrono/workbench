"""Explicit public-reference retrieval and an offline local reference library.

The provider resolves release-pinned URLs; clients can only download a cached
selection. Files are streamed, checked and expanded inside a private directory,
then published together with their provenance. No network is used by startup,
snapshot, local resolution or analysis-time provenance lookup.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import threading
import time
import uuid
import zlib

from pack_manager import filesystem_path, ordinary_windows_path
from pack_security import strict_json, PackError
from reference_provider import EnsemblArchiveProvider, ReferenceCancelled

CHUNK = 1024 * 1024
MAX_DOWNLOAD_BYTES = 100 * 1024**3
MAX_EXPANDED_BYTES = 500 * 1024**3
MAX_REGISTRY_BYTES = 16 * 1024**2
MAX_RECEIPT_BYTES = 1024 * 1024
MAX_RECORDS = 10000
MAX_SNAPSHOT_LOCAL_BYTES = 3 * 1024**2
DISK_FLOOR = 16 * 1024**2
KINDS = {'genome', 'annotation', 'cdna', 'ncrna', 'protein'}
SHA = re.compile(r'[0-9a-f]{64}\Z')
IDENTITY = re.compile(r'[0-9a-f]{32}\Z')


class ReferenceError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise ReferenceError(message)


def _cancelled(cancel):
    if cancel is not None and (cancel.is_set() if hasattr(cancel, 'is_set') else cancel()):
        raise ReferenceCancelled('Reference download cancelled; no incomplete reference was added.')


def _event(callback, phase, **fields):
    if callback:
        callback({'phase': phase, **fields})


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def _ordinary(path):
    return ordinary_windows_path(path) if os.name == 'nt' else str(path)


def _no_links(path):
    """Reject symlinks and Windows reparse points, including parent junctions."""
    path = filesystem_path(path)
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        _require(not stat.S_ISLNK(info.st_mode) and
                 not getattr(info, 'st_file_attributes', 0) & 0x400,
                 'Reference locations cannot use symbolic links or junctions.')
    return path


def _directory(path, create=False):
    path = _no_links(path)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    _require(path.is_dir(), 'Choose an existing reference destination folder.')
    return _no_links(path)


def _filename(value):
    _require(isinstance(value, str) and 1 <= len(value) <= 180 and
             value not in {'.', '..'} and not any(c in value for c in '/\\:*?"<>|') and
             all(ord(c) >= 32 and ord(c) != 127 for c in value) and
             not value.endswith((' ', '.')), 'Provider supplied an unsafe reference filename.')
    _require(value.split('.')[0].upper() not in
             {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
              *(f'LPT{i}' for i in range(1, 10))}, 'Provider supplied a reserved filename.')
    return value


def _read_json(path, limit):
    path = _no_links(path)
    _require(path.is_file() and path.stat().st_size <= limit, 'Reference metadata is missing or too large.')
    try:
        raw = path.read_bytes()
        _require(len(raw) <= limit, 'Reference metadata is too large.')
        return strict_json(raw), raw
    except PackError as exc:
        raise ReferenceError('Reference metadata is damaged; existing files were preserved.') from exc


def _atomic_json(path, value):
    raw = _json_bytes(value)
    _require(len(raw) <= MAX_REGISTRY_BYTES, 'The local reference library is full.')
    _no_links(path)
    fd, name = tempfile.mkstemp(prefix='_write-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _no_links(path)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _bsd_update(value, block):
    # Ensembl CHECKSUMS uses BSD sum -r over compressed bytes, not MD5/SysV.
    for byte in block:
        value = (((value >> 1) | ((value & 1) << 15)) + byte) & 0xffff
    return value


def _check_format(prefix, kind, filename):
    # GTF attributes and FASTA descriptions can contain UTF-8. Validate the
    # structural ASCII bytes only, without decoding a potentially partial prefix.
    lines = [line for line in bytes(prefix).splitlines() if line.strip()]
    if kind == 'annotation':
        rows = [line for line in lines if not line.startswith(b'#')]
        _require(bool(rows), 'Downloaded annotation contains no GTF feature rows.')
        fields = rows[0].split(b'\t')
        _require(len(fields) == 9 and fields[3].isdigit() and fields[4].isdigit() and
                 0 < int(fields[3]) <= int(fields[4]), 'Downloaded annotation does not have a GTF header/feature row.')
    else:
        _require(bool(lines) and lines[0].startswith(b'>') and len(lines[0]) > 1,
                 'Downloaded sequence file does not begin with a FASTA record.')
        _require(any(line and not line.startswith(b'>') for line in lines[1:]),
                 'Downloaded sequence file contains no sequence after its FASTA header.')


def _public(value):
    result = deepcopy(value)
    if isinstance(result, dict):
        for file in result.get('files', []):
            manifest = file.get('checksum_manifest')
            if isinstance(manifest, dict):
                manifest.pop('text', None)
    return result


class ReferenceManager:
    def __init__(self, app_root, provider=None):
        self.root = filesystem_path(app_root).absolute()
        self.data = self.root / 'user-data' / 'references'
        self.registry = self.data / 'library.json'
        self.provider = provider if provider is not None else EnsemblArchiveProvider()
        self.lock = threading.RLock()
        self._operation_lock = threading.Lock()
        self._releases = []
        self._species = []
        self._discovery = None
        self._selections = {}

    def _records(self):
        _no_links(self.registry)
        if not self.registry.exists():
            return []
        document, _ = _read_json(self.registry, MAX_REGISTRY_BYTES)
        _require(isinstance(document, dict) and type(document.get('schema')) is int and document['schema'] == 1 and
                 isinstance(document.get('records'), list) and len(document['records']) <= MAX_RECORDS,
                 'Unsupported or damaged local reference library.')
        seen = set()
        for record in document['records']:
            _require(isinstance(record, dict) and isinstance(record.get('id'), str) and
                     IDENTITY.fullmatch(record['id']) and record['id'] not in seen and
                     isinstance(record.get('folder'), str) and Path(record['folder']).is_absolute() and
                     isinstance(record.get('receipt_path'), str) and
                     isinstance(record.get('receipt_sha256'), str) and SHA.fullmatch(record['receipt_sha256']) and
                     isinstance(record.get('files'), list) and 1 <= len(record['files']) <= len(KINDS),
                     'Damaged local reference record; existing files were preserved.')
            seen.add(record['id'])
            ids, names = set(), set()
            for file in record['files']:
                _require(isinstance(file, dict) and file.get('id') in KINDS and file.get('kind') in KINDS and
                         file['id'] not in ids and type(file.get('bytes')) is int and file['bytes'] > 0 and
                         isinstance(file.get('sha256'), str) and SHA.fullmatch(file['sha256']) and
                         isinstance(file.get('path'), str), 'Damaged local reference file record.')
                name = _filename(file.get('filename'))
                _require(name.casefold() not in names and
                         filesystem_path(file['path']) == filesystem_path(record['folder']) / name,
                         'Reference file is outside its recorded bundle.')
                ids.add(file['id']); names.add(name.casefold())
            _require(filesystem_path(record['receipt_path']) == filesystem_path(record['folder']) / 'reference.json',
                     'Reference receipt is outside its recorded bundle.')
        return document['records']

    def snapshot(self):
        with self.lock:
            records, used = [], 0
            all_records = self._records()
            for raw_record in reversed(all_records):
                record = _public(raw_record)
                amount = len(_json_bytes(record))
                if used + amount > MAX_SNAPSHOT_LOCAL_BYTES:
                    break
                used += amount
                try:
                    self._verify_record(raw_record)
                    for file in record['files']:
                        self._verify_file(file)
                    record.update(available=True, status='ready', error='')
                except (ReferenceError, OSError) as exc:
                    record.update(available=False, status='unavailable', error=str(exc))
                records.append(record)
            records.reverse()
            omitted = len(all_records) - len(records)
            return {'schema': 1, 'providers': [deepcopy(self.provider.descriptor())],
                    'releases': deepcopy(self._releases), 'species': deepcopy(self._species),
                    'discovery': _public(self._discovery), 'local': records, 'omitted_local': omitted,
                    'default_destination': _ordinary(self.data),
                    'notice': 'Public reference discovery and downloads connect only when requested. '
                              'Downloaded files remain local. Ensembl archive releases are not the new Ensembl platform.' +
                              (f' Showing the newest {len(records)} bundles; {omitted} older bundles remain on disk.' if omitted else '')}

    def search(self, release, query, cancel=None, event=None):
        _cancelled(cancel)
        releases = self.provider.releases(cancel=cancel, event=event)
        species = self.provider.species(release, query=query, cancel=cancel, event=event)
        _cancelled(cancel)
        with self.lock:
            self._releases, self._species = deepcopy(releases), deepcopy(species)
            self._discovery = None
        return self.snapshot()

    def discover(self, release, species_id, cancel=None, event=None):
        _cancelled(cancel)
        discovery = deepcopy(self.provider.discover(release, species_id, cancel=cancel, event=event))
        _require(isinstance(discovery, dict) and isinstance(discovery.get('files'), list) and
                 1 <= len(discovery['files']) <= len(KINDS), 'Provider found no supported reference files.')
        selection_id = uuid.uuid4().hex
        discovery['selection_id'] = selection_id
        _cancelled(cancel)
        with self.lock:
            self._discovery = discovery
            self._selections[selection_id] = deepcopy(discovery)
            # Bounded session selections; old UI requests must rediscover explicitly.
            while len(self._selections) > 20:
                self._selections.pop(next(iter(self._selections)))
        return self.snapshot()

    def _verify_record(self, record):
        _directory(record['folder'])
        receipt, raw = _read_json(record['receipt_path'], MAX_RECEIPT_BYTES)
        _require(hashlib.sha256(raw).hexdigest() == record['receipt_sha256'],
                 'The reference provenance receipt has changed or is damaged.')
        _require(receipt == {key: value for key, value in record.items() if key != 'receipt_sha256'},
                 'The reference library does not agree with its original provenance receipt.')

    def _verify_file(self, file):
        path = _no_links(file['path'])
        _require(path.is_file(), 'A downloaded reference file is missing: ' + file['filename'])
        info = path.stat()
        _require(info.st_size == file['bytes'], 'A downloaded reference file has changed: ' + file['filename'])
        return path

    def _record(self, record_id):
        _require(isinstance(record_id, str), 'Invalid local reference identifier.')
        record = next((record for record in self._records() if record['id'] == record_id), None)
        _require(record is not None, 'This downloaded reference is no longer in the local library.')
        self._verify_record(record)
        return record

    def resolve_file(self, record_id, file_id):
        with self.lock:
            record = self._record(record_id)
            file = next((file for file in record['files'] if file['id'] == file_id), None)
            _require(file is not None, 'This file was not downloaded in the selected reference bundle.')
            self._verify_file(file)
            return {**_public({'files': [file]})['files'][0], 'record_id': record['id'], 'record_label': record.get('label', ''),
                    **{key: deepcopy(record.get(key)) for key in
                       ('provider', 'release', 'species', 'assembly', 'assembly_accession',
                        'receipt_path', 'receipt_sha256', 'downloaded_at')}}

    def record_folder(self, record_id):
        with self.lock:
            return _ordinary(_directory(self._record(record_id)['folder']))

    def provenance_for_path(self, path, sha256=None):
        key = os.path.normcase(_ordinary(filesystem_path(path).resolve()))
        with self.lock:
            for record in self._records():
                for file in record['files']:
                    if os.path.normcase(_ordinary(filesystem_path(file['path']).resolve())) != key:
                        continue
                    result = self.resolve_file(record['id'], file['id'])
                    if sha256 is not None:
                        _require(sha256 == file['sha256'],
                                 'A downloaded reference changed after retrieval. Restore the file or select an independent local copy.')
                    return {key: deepcopy(record.get(key)) for key in
                            ('provider', 'release', 'species', 'assembly', 'assembly_accession',
                             'receipt_path', 'receipt_sha256', 'downloaded_at', 'source_catalog')} | {
                                'record_id': record['id'], 'record_label': record.get('label', ''),
                                'file': _public({'files': [file]})['files'][0]}
        return None

    @staticmethod
    def _disk(path, needed=0):
        _require(shutil.disk_usage(path).free >= needed + DISK_FLOOR,
                 'There is not enough free disk space for this reference download.')

    def _download_file(self, item, folder, cancel, event, completed, expected_total, expanded_total):
        filename = _filename(item.get('filename'))
        _require(filename.endswith('.gz'), 'Only provider-resolved gzip reference files are supported.')
        name = _filename(filename[:-3])
        _require(item.get('id') in KINDS and item.get('kind') in KINDS,
                 'Provider supplied an unknown reference type.')
        size = item.get('bytes', item.get('size'))
        _require(size is None or type(size) is int and 0 < size <= MAX_DOWNLOAD_BYTES,
                 'Reference download exceeds the supported size.')
        checksum = item.get('checksum')
        _require(isinstance(checksum, dict) and checksum.get('algorithm') == 'bsd-sum' and
                 type(checksum.get('value')) is int and 0 <= checksum['value'] <= 65535 and
                 type(checksum.get('blocks')) is int and checksum['blocks'] > 0,
                 'Provider supplied no supported integrity checksum.')
        _cancelled(cancel)
        compressed_hash, expanded_hash = hashlib.sha256(), hashlib.sha256()
        compressed = expanded = bsd = members = 0
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        prefix = bytearray()
        started, last_progress, last_disk = time.monotonic(), 0.0, 0
        target = folder / name
        with self.provider.open_url(item['url'], cancel=cancel) as response, target.open('xb') as output:
            _require(response.getcode() == 200, 'Reference server did not return an ordinary file.')
            _require(response.headers.get('Content-Encoding', 'identity').lower() == 'identity',
                     'Reference server returned unsupported HTTP encoding.')
            length = response.headers.get('Content-Length')
            if length is not None:
                _require(length.isdecimal() and 0 < int(length) <= MAX_DOWNLOAD_BYTES,
                         'Reference server returned an invalid or excessive content length.')
                length = int(length)
                _require(size is None or length == size, 'Reference size changed since discovery; discover files again.')
            effective_url = response.geturl()
            response_info = {'etag': response.headers.get('ETag'), 'last_modified': response.headers.get('Last-Modified')}
            while True:
                _cancelled(cancel)
                _require(time.monotonic() - started < 48 * 3600, 'Reference download exceeded its 48-hour limit.')
                block = response.read(CHUNK)
                if not block:
                    break
                compressed += len(block)
                _require(completed + compressed <= MAX_DOWNLOAD_BYTES, 'Selected references exceed the compressed download limit.')
                _require(length is None or compressed <= length, 'Reference server sent more bytes than declared.')
                _require(size is None or compressed <= size, 'Reference server sent more bytes than discovered.')
                compressed_hash.update(block)
                bsd = _bsd_update(bsd, block)
                pending = block
                while pending:
                    _cancelled(cancel)
                    if decompressor.eof:
                        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
                    try:
                        plain = decompressor.decompress(pending, CHUNK)
                    except zlib.error as exc:
                        raise ReferenceError('Downloaded gzip data is corrupt or its CRC check failed: ' + filename) from exc
                    pending = decompressor.unused_data if decompressor.eof else decompressor.unconsumed_tail
                    if decompressor.eof:
                        members += 1
                    expanded += len(plain)
                    _require(expanded_total + expanded <= MAX_EXPANDED_BYTES,
                             'Expanded reference files exceed the supported size limit.')
                    if len(prefix) < 65536:
                        prefix.extend(plain[:65536 - len(prefix)])
                    if plain:
                        if expanded - last_disk >= 8 * CHUNK or last_disk == 0:
                            self._disk(folder, len(plain))
                            last_disk = expanded
                        expanded_hash.update(plain)
                        output.write(plain)
                now = time.monotonic()
                if now - last_progress >= .15:
                    _event(event, 'downloading', message='Downloading and checking ' + item.get('label', filename),
                           filename=filename, bytes=completed + compressed, total=expected_total,
                           expanded_bytes=expanded_total + expanded, cancellable=True)
                    last_progress = now
            _require(compressed > 0 and (length is None or compressed == length) and
                     (size is None or compressed == size), 'Reference download was truncated; no reference was added.')
            _require(decompressor.eof and members > 0, 'Downloaded gzip file is incomplete; no reference was added.')
            _require(bsd == checksum['value'] and (compressed + 1023) // 1024 == checksum['blocks'],
                     'Reference does not match the provider BSD checksum; no reference was added.')
            _check_format(prefix, item['kind'], filename)
            output.flush()
            os.fsync(output.fileno())
        _cancelled(cancel)
        return {**deepcopy(item), 'id': item['id'], 'kind': item['kind'], 'label': item.get('label', item['kind']),
                'filename': name, 'source_filename': filename, 'bytes': expanded,
                'sha256': expanded_hash.hexdigest(), 'compressed_bytes': compressed,
                'compressed_sha256': compressed_hash.hexdigest(), 'source_url': item['url'],
                'effective_url': effective_url, 'checksum': deepcopy(checksum),
                'checksum_manifest': deepcopy(item.get('checksum_manifest')),
                'sequence_choice': item.get('sequence_scope', item.get('sequence_choice', item.get('sequence_set'))),
                'masking': item.get('masking'), 'format': item.get('format', 'gtf' if item['kind'] == 'annotation' else 'fasta'),
                'validation': {'gzip_crc': 'passed', 'provider_bsd_sum': 'passed', 'format_header': 'passed (basic prefix only)',
                               'sha256': 'computed locally; not a publisher signature'}, **response_info}

    def download(self, selection_id, file_ids, destination, cancel=None, event=None):
        _require(self._operation_lock.acquire(blocking=False), 'Another reference download is already running.')
        try:
            return self._download(selection_id, file_ids, destination, cancel, event)
        finally:
            self._operation_lock.release()

    def _download(self, selection_id, file_ids, destination, cancel, event):
        with self.lock:
            selection = deepcopy(self._selections.get(selection_id)) if isinstance(selection_id, str) else None
        _require(selection is not None, 'This reference selection expired. Discover its files again.')
        _require(isinstance(file_ids, list) and 1 <= len(file_ids) <= len(KINDS) and
                 all(isinstance(value, str) for value in file_ids) and len(set(file_ids)) == len(file_ids),
                 'Select one or more distinct reference files.')
        by_id = {file['id']: file for file in selection['files']}
        _require(all(identity in by_id for identity in file_ids), 'A requested file was not in this reference discovery.')
        items = [by_id[identity] for identity in file_ids]
        names = [_filename(item['filename'])[:-3].casefold() for item in items]
        _require(len(set(names)) == len(names) and 'reference.json' not in names, 'Provider filenames collide.')
        _require(isinstance(destination, str) and destination and len(destination) < 32700 and
                 Path(destination).is_absolute(), 'Choose an absolute reference destination folder.')
        _cancelled(cancel)
        destination_path = filesystem_path(destination).absolute()
        destination_path = _directory(destination_path, create=destination_path == self.data)
        expected = [item.get('bytes', item.get('size')) for item in items]
        _require(all(size is None or type(size) is int and 0 < size <= MAX_DOWNLOAD_BYTES for size in expected),
                 'Provider supplied an invalid reference size.')
        known_total = sum(size for size in expected if size is not None)
        _require(known_total <= MAX_DOWNLOAD_BYTES, 'Selected references exceed the compressed download limit.')
        expected_total = known_total if all(size is not None for size in expected) else None
        self._disk(destination_path, known_total)
        identity = uuid.uuid4().hex
        final = destination_path / ('ref-' + identity[:16])
        _require(not final.exists() and not final.is_symlink(), 'Reference destination already exists; existing files were preserved.')
        temporary = Path(tempfile.mkdtemp(prefix='_ref-', dir=destination_path))
        published = registered = False
        try:
            files, completed, expanded = [], 0, 0
            for item in items:
                file = self._download_file(item, temporary, cancel, event, completed, expected_total, expanded)
                file['path'] = _ordinary(final / file['filename'])
                files.append(file)
                completed += file['compressed_bytes']; expanded += file['bytes']
            _cancelled(cancel)
            record = {key: deepcopy(value) for key, value in selection.items() if key not in {'files', 'selection_id'}}
            species = selection.get('species', 'Reference')
            species_name = species.get('name', species.get('id', 'Reference')) if isinstance(species, dict) else str(species)
            assembly = selection.get('assembly') or (species.get('assembly', '') if isinstance(species, dict) else '')
            record.update(schema=1, id=identity, label=selection.get('label') or
                          (species_name + (' — ' + assembly if assembly else '') +
                           ' — release ' + str(selection.get('release', ''))),
                          folder=_ordinary(final), receipt_path=_ordinary(final / 'reference.json'), files=files,
                          downloaded_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                          integrity_notice='Provider BSD checksums detect transfer errors; local SHA-256 records file identity. Neither is a publisher signature.')
            raw = _json_bytes(record)
            _require(len(raw) <= MAX_RECEIPT_BYTES, 'Reference provenance is unexpectedly large.')
            with (temporary / 'reference.json').open('xb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            record['receipt_sha256'] = hashlib.sha256(raw).hexdigest()
            with self.lock:
                _directory(self.data, create=True)
                lockpath = self.data / '_publish.lock'
                _no_links(lockpath)
                try:
                    lockfd = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                except FileExistsError as exc:
                    raise ReferenceError('Another Workbench instance is updating the reference library. '
                                         'Retry after it finishes. A lock left after an interrupted update may need removal.') from exc
                try:
                    os.close(lockfd)
                    records = self._records()
                    _require(len(records) < MAX_RECORDS, 'The local reference library is full.')
                    _require(not final.exists() and not final.is_symlink(),
                             'Reference destination already exists; existing files were preserved.')
                    _directory(destination_path)
                    _cancelled(cancel)
                    _event(event, 'publishing', message='Adding the verified reference to your local library.',
                           bytes=completed, total=expected_total, cancellable=False)
                    os.rename(temporary, final)
                    published = True
                    _atomic_json(self.registry, {'schema': 1, 'records': [*records, record]})
                    registered = True
                finally:
                    lockpath.unlink(missing_ok=True)
            return self.snapshot()
        except (ReferenceError, ReferenceCancelled):
            if published and not registered:
                shutil.rmtree(final, ignore_errors=True)
            raise
        except (OSError, ValueError) as exc:
            if published and not registered:
                shutil.rmtree(final, ignore_errors=True)
            raise ReferenceError('Reference retrieval failed. Check the connection, destination permissions and available disk space.') from exc
        finally:
            if temporary.exists():
                shutil.rmtree(temporary, ignore_errors=True)
