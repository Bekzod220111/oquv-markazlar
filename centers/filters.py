import django_filters
from django.db.models import Q
import unicodedata
from difflib import SequenceMatcher
from .models import Center


class CenterFilter(django_filters.FilterSet):
    subject = django_filters.CharFilter(field_name="subjects__slug")
    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = Center
        fields = ["subject", "q"]

    def filter_q(self, queryset, name, value):
        value = unicodedata.normalize("NFKC", value).strip().lower()
        if not value:
            return queryset

        qs = queryset.filter(
            Q(name__icontains=value)
            | Q(alternative_names__icontains=value)
            | Q(address__icontains=value)
            | Q(description__icontains=value)
            | Q(subjects__name__icontains=value)
            | Q(subjects__alternative_names__icontains=value)
            | Q(courses__name__icontains=value)
            | Q(courses__alternative_names__icontains=value)
        ).distinct()

        # SAT and similar short terms should match course/category records even
        # when a center name is unrelated.
        if qs.count():
            return qs

        matches = []
        for center in queryset.prefetch_related("subjects", "courses"):
            candidates = [center.name, center.address, center.description, center.alternative_names]
            candidates += [s.name + " " + s.alternative_names for s in center.subjects.all()]
            candidates += [c.name + " " + c.alternative_names for c in center.courses.all()]
            normalized = [
                unicodedata.normalize("NFKC", item or "").lower()
                for item in candidates
            ]
            if any(value in item or SequenceMatcher(None, value, item).ratio() >= 0.72 for item in normalized):
                matches.append(center.pk)
        return queryset.filter(pk__in=matches)
