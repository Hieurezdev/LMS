"""Restore database records and uploaded files from an LMS backup archive."""

import json
import shutil
import tarfile
import tempfile
from pathlib import Path

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore database records and uploaded media from a backup archive."

    def add_arguments(self, parser):
        parser.add_argument("input", help="Path to a .tar.gz backup archive.")
        parser.add_argument(
            "--yes-i-really-want-to-restore",
            action="store_true",
            help="Confirm that current database/media data may be changed.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Flush current database data before loading the backup.",
        )
        parser.add_argument(
            "--replace-media",
            action="store_true",
            help="Replace the current media directory instead of merging files.",
        )

    def handle(self, *args, **options):
        if not options["yes_i_really_want_to_restore"]:
            raise CommandError(
                "Restoring changes application data. Re-run with "
                "--yes-i-really-want-to-restore."
            )

        archive_path = Path(options["input"]).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="lms-restore-") as temp_dir:
            extracted_path = Path(temp_dir)
            self._extract_archive(archive_path, extracted_path)
            manifest_path = extracted_path / "manifest.json"
            database_path = extracted_path / "database.json"
            if not manifest_path.exists() or not database_path.exists():
                raise CommandError("Backup must contain manifest.json and database.json")
            self._read_manifest(manifest_path)

            management.call_command("migrate", interactive=False, verbosity=0)
            if options["replace"]:
                management.call_command("flush", interactive=False, verbosity=0)
            management.call_command("loaddata", str(database_path), verbosity=0)

            media_path = extracted_path / "media"
            if media_path.exists():
                self._restore_media(media_path, options["replace_media"])

        self.stdout.write(self.style.SUCCESS(f"Backup restored: {archive_path}"))

    @staticmethod
    def _extract_archive(archive_path, destination):
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                for member in archive.getmembers():
                    member_path = Path(member.name)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise CommandError(f"Unsafe path in backup archive: {member.name}")
                archive.extractall(destination)
        except (OSError, tarfile.TarError) as exc:
            raise CommandError(f"Could not read backup archive {archive_path}: {exc}") from exc

    @staticmethod
    def _read_manifest(manifest_path):
        try:
            with manifest_path.open(encoding="utf-8") as manifest_file:
                manifest = json.load(manifest_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Invalid backup manifest: {exc}") from exc
        if manifest.get("database") != "database.json":
            raise CommandError("Backup manifest does not describe database.json")

    @staticmethod
    def _restore_media(source, replace):
        media_root = Path(settings.MEDIA_ROOT)
        if replace and media_root.exists():
            shutil.rmtree(media_root)
        media_root.mkdir(parents=True, exist_ok=True)
        for source_path in source.rglob("*"):
            destination = media_root / source_path.relative_to(source)
            if source_path.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif source_path.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
