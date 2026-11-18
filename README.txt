Repo ildiziga (manage.py turgan joyga) shu papkalarni ustidan nusxala:
  centers/*.py  config/urls.py  templates/  static/

config/settings.py ga:
  TEMPLATES -> "DIRS": [BASE_DIR / "templates"],
  oxiriga:     STATICFILES_DIRS = [BASE_DIR / "static"]

Keyin:
  python manage.py makemigrations
  python manage.py migrate
  python manage.py runserver
