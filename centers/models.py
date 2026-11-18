from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    alternative_names = models.TextField(blank=True, help_text="Vergul bilan: Ingliz tili, English, АНГЛИЙСКИЙ")

    def __str__(self):
        return self.name


class Center(models.Model):
    name = models.CharField(max_length=200)
    alternative_names = models.TextField(blank=True)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    instagram = models.CharField(max_length=255, blank=True)
    telegram = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    rating = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)
    working_hours = models.CharField(max_length=255, blank=True)
    price_monthly = models.PositiveIntegerField(
        null=True, blank=True, help_text="Oyiga narxi (so'm)"
    )
    price_min = models.PositiveIntegerField(null=True, blank=True)
    price_max = models.PositiveIntegerField(null=True, blank=True)
    image_url = models.URLField(blank=True, help_text="Rasm havolasi (ixtiyoriy)")
    subjects = models.ManyToManyField(Subject, related_name="centers")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=200)
    alternative_names = models.TextField(blank=True)
    category = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="courses")
    centers = models.ManyToManyField(Center, related_name="courses")
    price_min = models.PositiveIntegerField(null=True, blank=True)
    price_max = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class CenterImage(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="centers/")
    alt = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.alt or f"{self.center.name} image"


class Review(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name="reviews")
    author = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.center.name}: {self.rating}/5"
