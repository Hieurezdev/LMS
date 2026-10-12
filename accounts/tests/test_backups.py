import json
import os
import tarfile
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from lms_manager.management.commands.backup_data import Command


class BackupListingTests(TestCase):
    def test_corrupt_archive_does_not_break_admin_pages(self):
        with TemporaryDirectory() as backup_root:
            archive_path = Path(backup_root) / "lms-backup-incomplete.tar.gz"
            manifest = json.dumps({"created_at": "2026-10-12T06:30:00+00:00"}).encode()
            with tarfile.open(archive_path, "w:gz") as archive:
                member = tarfile.TarInfo("manifest.json")
                member.size = len(manifest)
                archive.addfile(member, BytesIO(manifest))
                payload = os.urandom(32768)
                member = tarfile.TarInfo("media/large.bin")
                member.size = len(payload)
                archive.addfile(member, BytesIO(payload))
            archive_bytes = archive_path.read_bytes()
            archive_path.write_bytes(archive_bytes[:len(archive_bytes) // 2])
            with self.assertRaises(EOFError):
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractfile("manifest.json")

            admin = get_user_model().objects.create_superuser(
                username="backup-admin", password="safe-test-password"
            )
            self.client.force_login(admin)
            with override_settings(BACKUP_ROOT=backup_root), translation.override("en"):
                for view_name in ("admin_panel", "backup_center"):
                    with self.subTest(view_name=view_name):
                        response = self.client.get(reverse(view_name))
                        self.assertEqual(response.status_code, 200)
                        self.assertContains(response, "Không đọc được")
                        self.assertEqual(response.context["unreadable_backup_count"], 1)
            self.assertTrue(archive_path.exists())


class BackupCreationTests(SimpleTestCase):
    def test_failed_archive_is_not_published_or_left_behind(self):
        with TemporaryDirectory() as backup_root:
            output_path = Path(backup_root) / "lms-backup-test.tar.gz"
            with override_settings(BACKUP_ROOT=backup_root, MEDIA_ROOT=str(Path(backup_root) / "media")):
                with patch.object(Command, "_all_objects", return_value=iter(())):
                    with patch("tarfile.TarFile.add", side_effect=OSError("simulated write failure")):
                        with self.assertRaises(CommandError):
                            call_command("backup_data", output=str(output_path), verbosity=0)

                self.assertFalse(output_path.exists())
                self.assertEqual(list(Path(backup_root).glob(".lms-backup-*.tmp")), [])

                with patch.object(Command, "_all_objects", return_value=iter(())):
                    call_command("backup_data", output=str(output_path), verbosity=0)

            with tarfile.open(output_path, "r:gz") as archive:
                self.assertIn("manifest.json", archive.getnames())
            self.assertEqual(list(Path(backup_root).glob(".lms-backup-*.tmp")), [])
