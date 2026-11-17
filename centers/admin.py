from django.contrib import admin
from .models import Subject, Center

# Register your models here.


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Center)
class CenterAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "rating")
    list_filter = ("subjects",)
    search_fields = ("name", "address")