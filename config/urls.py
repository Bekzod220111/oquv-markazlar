from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from centers.views import AboutView, HomeView, MapView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("centers.urls")),
    path("about/<int:pk>/", AboutView.as_view(), name="about"),
    path("map/", MapView.as_view(), name="map"),
    path("", HomeView.as_view(), name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
