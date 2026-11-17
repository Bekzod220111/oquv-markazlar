from django.db import models


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Center(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    rating = models.FloatField(default=0)
    subjects = models.ManyToManyField(Subject, related_name="centers")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name