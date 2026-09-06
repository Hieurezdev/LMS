"""Create a portable backup archive for the LMS database and uploaded files."""

import json
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.db import DatabaseError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Back up the Django database data and uploaded media to one tar.gz file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            help="Destination archive path (defaults to BACKUP_ROOT with a UTC timestamp).",
        )
        parser.add_argument(
            "--keep",
            type=int,
            help="Keep only this many generated backups after a successful backup.",
        )

    def handle(self, *args, **options):
        if options["keep"] is not None and options["keep"] < 1:
            raise CommandError("--keep must be at least 1")
        created_at = datetime.now(timezone.utc)
        archive_path = self._archive_path(options["output"], created_at)
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        if archive_path.exists():
            raise CommandError(f"Backup file already exists: {archive_path}")

        with tempfile.TemporaryDirectory(prefix="lms-backup-") as temp_dir:
            temp_path = Path(temp_dir)
            database_path = temp_path / "database.json"
            manifest_path = temp_path / "manifest.json"

            try:
                with database_path.open("w", encoding="utf-8") as database_file:
                    serializers.serialize(
                        "json",
                        self._all_objects(),
                        indent=2,
                        stream=database_file,
                    )
            except (DatabaseError, OSError) as exc:
                raise CommandError(
                    f"Could not read the database. Check database availability: {exc}"
                ) from exc

            manifest_path.write_text(
                json.dumps(
                    {
                        "created_at": created_at.isoformat(),
                        "database": "database.json",
                        "media": "media/",
                        "restore": "Run migrations, then: python manage.py loaddata database.json",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            try:
                with tarfile.open(archive_path, "w:gz") as archive:
                    archive.add(database_path, arcname="database.json")
                    archive.add(manifest_path, arcname="manifest.json")
                    media_root = Path(settings.MEDIA_ROOT)
                    if media_root.exists():
                        archive.add(media_root, arcname="media")
            except (OSError, tarfile.TarError) as exc:
                archive_path.unlink(missing_ok=True)
                raise CommandError(f"Could not create backup {archive_path}: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Backup created: {archive_path}"))
        if options["keep"] is not None:
            self._remove_old_backups(options["keep"], archive_path)

    @staticmethod
    def _all_objects():
        """Return every installed model instance, including authentication data."""
        from django.apps import apps

        for model in apps.get_models():
            yield from model._base_manager.all().iterator()

    @staticmethod
    def _archive_path(output, created_at):
        if output:
            return Path(output).expanduser().resolve()
        timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
        return Path(settings.BACKUP_ROOT) / f"lms-backup-{timestamp}.tar.gz"

    @staticmethod
    def _remove_old_backups(keep, current_path):
        backup_paths = sorted(
            Path(settings.BACKUP_ROOT).glob("lms-backup-*.tar.gz"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for old_path in backup_paths[keep:]:
            if old_path != current_path:
                old_path.unlink()
