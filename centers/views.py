from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from django.db.models import Avg, Count, F, Max, Min, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce

from .models import Subject, Center, Course, Review
from .serializers import SubjectSerializer, CenterSerializer, CenterMapSerializer
from .filters import CenterFilter
from .search import search_center_ids, text_matches
from .utils import haversine


# ---------- Sahifalar (HTML) ----------
class MapView(TemplateView):
    template_name = "map.html"


class AboutView(TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["center"] = get_object_or_404(
            Center.objects.filter(is_active=True).prefetch_related(
                "subjects", "courses", "images", "reviews"
            ),
            pk=kwargs["pk"],
        )
        return context


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["centers"] = Center.objects.filter(is_active=True).prefetch_related("subjects").order_by("-rating", "name")
        context["subjects"] = Subject.objects.annotate(center_count=models.Count("centers", filter=Q(centers__is_active=True))).order_by("name")
        return context


# ---------- API ----------
def annotated_centers():
    """Faol markazlar + hisoblangan reyting va narx oralig'i (subquery: join takrorlanmaydi)."""
    reviews = Review.objects.filter(center=OuterRef("pk")).order_by().values("center")
    courses = Course.objects.filter(centers=OuterRef("pk")).order_by().values("centers")
    return Center.objects.filter(is_active=True).annotate(
        _avg=Subquery(reviews.annotate(a=Avg("rating")).values("a")),
        review_count=Coalesce(Subquery(reviews.annotate(n=Count("pk")).values("n")), 0),
        _cmin=Subquery(courses.annotate(m=Min("price_min")).values("m")),
        _cmax=Subquery(courses.annotate(m=Max("price_max")).values("m")),
    ).annotate(
        rating_value=Coalesce(F("_avg"), F("rating")),
        price_min_value=Coalesce(F("_cmin"), F("price_min"), F("price_monthly")),
        price_max_value=Coalesce(F("_cmax"), F("price_max"), F("price_monthly")),
    )


def _finish(center):
    center.rating = round(center.rating_value or 0, 1)
    center.price_min = center.price_min_value
    center.price_max = center.price_max_value
    return center


class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    pagination_class = None


class CenterListView(generics.ListAPIView):
    """Xarita ro'yxati: ?north&south&east&west&q&subject&lat&lon&sort"""
    serializer_class = CenterMapSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CenterFilter
    pagination_class = None
    MAX_RESULTS = 300

    def get_queryset(self):
        return annotated_centers()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        params = request.query_params
        edges = [params.get(k) for k in ("north", "south", "east", "west")]
        if any(v is not None for v in edges):
            try:
                north, south, east, west = (float(v) for v in edges)
            except (TypeError, ValueError):
                return Response({"error": "north, south, east va west raqam bo'lishi kerak"}, status=400)
            if not (-90 <= south <= north <= 90 and -180 <= west <= 180 and -180 <= east <= 180):
                return Response({"error": "Xarita chegaralari noto'g'ri"}, status=400)
            qs = qs.filter(latitude__gte=south, latitude__lte=north)
            if west <= east:
                qs = qs.filter(longitude__gte=west, longitude__lte=east)
            else:  # 180-meridian orqali o'tadigan oyna
                qs = qs.filter(Q(longitude__gte=west) | Q(longitude__lte=east))

        qs = self.filter_queryset(qs).distinct()

        lat, lon = params.get("lat"), params.get("lon")
        has_location = False
        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
            except ValueError:
                return Response({"error": "lat va lon raqam bo'lishi kerak"}, status=400)
            has_location = True

        centers = [_finish(c) for c in qs]
        if has_location:
            for c in centers:
                c.distance_km = round(haversine(lat, lon, c.latitude, c.longitude), 2)

        sort = params.get("sort")
        if sort == "rating":
            centers.sort(key=lambda c: -c.rating)
        elif sort == "price_asc":
            centers.sort(key=lambda c: (c.price_min is None, c.price_min or 0))
        elif sort == "price_desc":
            centers.sort(key=lambda c: (c.price_max is None, -(c.price_max or 0)))
        elif has_location:
            centers.sort(key=lambda c: c.distance_km)

        return Response(self.get_serializer(centers[: self.MAX_RESULTS], many=True).data)


class CenterDetailView(generics.RetrieveAPIView):
    serializer_class = CenterSerializer

    def get_queryset(self):
        return annotated_centers().prefetch_related("subjects", "courses", "courses__category", "images")

    def get_object(self):
        center = _finish(super().get_object())
        center.reviews_list = list(center.reviews.order_by("-created_at")[:20])
        return center


class SuggestView(APIView):
    """Qidiruv tagida chiqadigan takliflar: kurslar, yo'nalishlar, markazlar. ?q=sat"""
    LIMIT = 5

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()[:100]
        if not q:
            return Response({"courses": [], "subjects": [], "centers": []})

        active = Q(centers__is_active=True)
        courses = []
        for c in Course.objects.annotate(n=Count("centers", filter=active, distinct=True)).filter(n__gt=0):
            if text_matches(q, c.name, c.alternative_names):
                courses.append({"type": "course", "id": c.id, "name": c.name, "center_count": c.n})
        subjects = []
        for s in Subject.objects.annotate(n=Count("centers", filter=active, distinct=True)).filter(n__gt=0):
            if text_matches(q, s.name, s.alternative_names):
                subjects.append({"type": "subject", "slug": s.slug, "name": s.name, "center_count": s.n})

        ids = search_center_ids(q) or set()
        centers = [
            {"type": "center", "id": c.id, "name": c.name, "address": c.address,
             "rating": round(c.rating_value or 0, 1), "latitude": c.latitude, "longitude": c.longitude}
            for c in annotated_centers().filter(pk__in=ids).order_by("-rating_value", "name")[: self.LIMIT]
        ]
        courses.sort(key=lambda x: -x["center_count"])
        subjects.sort(key=lambda x: -x["center_count"])
        return Response({"courses": courses[: self.LIMIT], "subjects": subjects[:3], "centers": centers})
