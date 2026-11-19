import django_filters

from .models import Center
from .search import search_center_ids


class CenterFilter(django_filters.FilterSet):
    subject = django_filters.CharFilter(field_name="subjects__slug")
    course = django_filters.NumberFilter(field_name="courses__id")
    q = django_filters.CharFilter(method="filter_q")

    class Meta:
        model = Center
        fields = ["subject", "course", "q"]

    def filter_q(self, queryset, name, value):
        ids = search_center_ids(value)
        if ids is None:
            return queryset
        return queryset.filter(pk__in=ids)
