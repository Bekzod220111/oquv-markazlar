from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from difflib import SequenceMatcher
import unicodedata

from .models import Subject, Center
from .serializers import SubjectSerializer, CenterSerializer
from .filters import CenterFilter
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
        context["centers"] = Center.objects.prefetch_related("subjects").order_by("-rating", "name")
        context["subjects"] = Subject.objects.annotate(center_count=models.Count("centers")).order_by("name")
        return context


# ---------- API ----------
class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    pagination_class = None


class CenterListView(generics.ListAPIView):
    queryset = Center.objects.filter(is_active=True).prefetch_related("subjects", "courses", "courses__category", "images", "reviews")
    serializer_class = CenterSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = CenterFilter

    def list(self, request, *args, **kwargs):
        centers = list(self.filter_queryset(self.get_queryset()))

        north = request.query_params.get("north")
        south = request.query_params.get("south")
        east = request.query_params.get("east")
        west = request.query_params.get("west")
        if any(v is not None for v in (north, south, east, west)):
            try:
                bounds = tuple(float(v) for v in (north, south, east, west))
            except (TypeError, ValueError):
                return Response({"error": "north, south, east va west raqam bo'lishi kerak"}, status=400)
            north, south, east, west = bounds
            if not (-90 <= south <= north <= 90 and -180 <= west <= 180 and -180 <= east <= 180):
                return Response({"error": "Xarita chegaralari noto'g'ri"}, status=400)
            centers = [c for c in centers if south <= c.latitude <= north and west <= c.longitude <= east]

        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        has_location = False
        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
            except ValueError:
                return Response({"error": "lat va lon raqam bo'lishi kerak"}, status=400)
            has_location = True
            for c in centers:
                c.distance_km = round(haversine(lat, lon, c.latitude, c.longitude), 2)

        # Tartiblash: ?sort=distance | rating | price_asc | price_desc
        sort = request.query_params.get("sort")
        if sort == "rating":
            centers.sort(key=lambda c: -c.rating)
        elif sort == "price_asc":
            # narxi yo'q markazlar oxirida
            centers.sort(key=lambda c: (c.price_monthly is None, c.price_monthly or 0))
        elif sort == "price_desc":
            centers.sort(key=lambda c: (c.price_monthly is None, -(c.price_monthly or 0)))
        elif has_location:
            centers.sort(key=lambda c: c.distance_km)

        serializer = self.get_serializer(centers, many=True)
        return Response(serializer.data)


class CenterDetailView(generics.RetrieveAPIView):
    queryset = Center.objects.filter(is_active=True).prefetch_related(
        "subjects", "courses", "courses__category", "images", "reviews"
    )
    serializer_class = CenterSerializer
