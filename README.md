# oquv-markazlar

## Database setup

```powershell
python manage.py migrate
```

SQLite remains the local default. To use PostgreSQL, install the declared
requirements and set `DATABASE_URL` to a PostgreSQL connection URL before
starting Django, for example:

```powershell
$env:DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE"
```