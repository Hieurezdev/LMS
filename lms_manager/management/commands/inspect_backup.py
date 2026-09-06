"""Inspect a backup archive without changing application data."""

import json
import tarfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Read and validate the manifest and contents of an LMS backup archive."

    def add_arguments(self, parser):
        parser.add_argument("input", help="Path to a .tar.gz backup archive.")

    def handle(self, *args, **options):
        archive_path = Path(options["input"]).expanduser().resolve()
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                members = archive.getmembers()
                self._validate_members(members)
                manifest_member = archive.getmember("manifest.json")
                manifest = json.load(archive.extractfile(manifest_member))
        except (OSError, KeyError, tarfile.TarError, json.JSONDecodeError) as exc:
            raise CommandError(f"Invalid backup archive {archive_path}: {exc}") from exc

        if "database.json" not in {member.name for member in members}:
            raise CommandError("Backup does not contain database.json")

        media_files = sum(
            1 for member in members if member.name.startswith("media/") and member.isfile()
        )
        self.stdout.write(f"Backup: {archive_path}")
        self.stdout.write(f"Created at: {manifest.get('created_at', 'unknown')}")
        self.stdout.write(f"Media files: {media_files}")
        self.stdout.write(self.style.SUCCESS("Backup is valid and ready to restore."))

    @staticmethod
    def _validate_members(members):
        for member in members:
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise CommandError(f"Unsafe path in backup archive: {member.name}")
