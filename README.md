# Taking the project to the next level on **https://github.com/SkyCascade/SkyLearn** 🚀

# Repository Moved to [SkyCascade/SkyLearn](https://github.com/SkyCascade/SkyLearn) and no longer maintained here

### Please update your bookmarks and direct all issues and pull requests to the new repository.

---

*Note: This repository is archived and read-only.*

### CORS security

CORS is enabled with an empty allow-list by default, so external websites
cannot read the application's API responses. If a separate frontend needs
access, add only its complete HTTPS origin to `.env`, for example:

```env
CORS_ALLOWED_ORIGINS=https://frontend.example.com
CSRF_TRUSTED_ORIGINS=https://frontend.example.com
```

Do not use `*` or enable credentials for untrusted origins.

### Backups

Create one compressed archive containing all database records and uploaded media:

```bash
uv run python manage.py backup_data
```

The archive is written to `backups/` by default. A custom destination can be
provided with `--output /path/to/lms-backup.tar.gz`. To restore the database,
extract the archive, run migrations, and load `database.json` with
`python manage.py loaddata database.json`; copy the archive's `media/` directory
back to `MEDIA_ROOT`.

When using Docker Compose, the `backup` service creates a backup immediately
and then once every hour. It keeps the 48 newest backups (approximately two
days) and deletes older ones after a successful backup. Start it with:

```bash
docker compose up -d backup
```

Inspect a backup without changing data:

```bash
uv run python manage.py inspect_backup backups/lms-backup-YYYYMMDDTHHMMSSZ.tar.gz
```

Restore by merging records and media into the current installation:

```bash
uv run python manage.py restore_data backups/lms-backup-YYYYMMDDTHHMMSSZ.tar.gz \
  --yes-i-really-want-to-restore
```

For a complete replacement, add `--replace --replace-media`. Always create a
new backup before using replacement mode.

---

### Learning management system using django web framework

Feature-rich learning management system. You may want to build a learning management system(AKA school management system) for a school organization or just for the sake of learning the tech stack and building your portfolio, either way, this project would be a good kickstart for you.

![Screenshot from 2023-12-31 17-36-31](https://github.com/adilmohak/django-lms/assets/60693922/e7fb628a-6275-4160-ae0f-ab27099ab3ca)
