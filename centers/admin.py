from django.contrib import admin
from .models import Subject, Center, Course, CenterImage, Review


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "alternative_names")


class CenterImageInline(admin.TabularInline):
    model = CenterImage
    extra = 3


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1


@admin.register(Center)
class CenterAdmin(admin.ModelAdmin):
    change_form_template = "admin/centers/center/change_form.html"
    inlines = [CenterImageInline, ReviewInline]
    list_display = ("name", "address", "rating", "price_min", "price_max", "is_active")
    list_editable = ("is_active",)
    list_filter = ("subjects",)
    search_fields = ("name", "alternative_names", "address", "subjects__name")
    autocomplete_fields = ("subjects",)
    fields = (
        "name", "alternative_names", "description", "address",
        "latitude", "longitude", "phone", "email", "website", "instagram", "telegram",
        "working_hours", "rating", "price_monthly", "price_min", "price_max",
        "image_url", "subjects", "is_active",
    )


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_min", "price_max")
    list_filter = ("category",)
    search_fields = ("name", "alternative_names", "category__name", "category__alternative_names")
    filter_horizontal = ("centers",)
