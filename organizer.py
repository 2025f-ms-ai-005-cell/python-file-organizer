"""Safe, copy-only file organization. Preview by default; never deletes sources."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

GROUPS = {
    'Documents': {'.pdf', '.docx', '.txt', '.md', '.csv', '.xlsx'},
    'Images': {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'},
    'Code': {'.py', '.dart', '.kt', '.java', '.js', '.html', '.css'},
    'Archives': {'.zip', '.tar', '.gz', '.7z'},
}


def category(path):
    return next((name for name, extensions in GROUPS.items()
                 if path.suffix.lower() in extensions), 'Other')


def plan(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_dir():
        raise ValueError('Source must be an existing directory')
    if destination == source or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError('Use separate, non-overlapping source and destination directories')
    entries = []
    for item in sorted(source.iterdir(), key=lambda p: p.name.lower()):
        if item.is_symlink() or not item.is_file() or item.name.startswith('.'):
            continue
        target = destination / category(item) / item.name
        entries.append({'source': str(item), 'destination': str(target),
                        'category': category(item), 'bytes': item.stat().st_size,
                        'status': 'skip-existing' if target.exists() else 'ready'})
    return entries


def digest(path):
    result = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def apply(entries):
    """Copy exclusively; collisions are skipped, and original files stay in place."""
    results = []
    for entry in entries:
        item = dict(entry)
        source, target = Path(item['source']), Path(item['destination'])
        created = False
        try:
            if source.is_symlink() or not source.is_file():
                raise ValueError('Source is no longer a regular file')
            target.parent.mkdir(parents=True, exist_ok=True)
            # Reject symlinked category directories; never overwrite a target.
            if target.parent.is_symlink():
                raise ValueError('Destination category must not be a symlink')
            with source.open('rb') as incoming, target.open('xb') as outgoing:
                created = True
                shutil.copyfileobj(incoming, outgoing)
            if digest(source) != digest(target):
                raise ValueError('Verification failed; source may have changed during copy')
            item['status'] = 'copied-verified'
        except FileExistsError:
            item['status'] = 'skip-existing'
        except (OSError, ValueError) as error:
            item['status'] = 'error'
            item['error'] = str(error)
            if created:
                target.unlink(missing_ok=True)
        results.append(item)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('--apply', action='store_true', help='Copy files; originals remain untouched')
    args = parser.parse_args()
    try:
        entries = plan(args.source, args.destination)
        if args.apply:
            entries = apply(entries)
        print(json.dumps({'mode': 'copy' if args.apply else 'preview', 'files': entries}, indent=2))
        return 1 if any(item['status'] == 'error' for item in entries) else 0
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
