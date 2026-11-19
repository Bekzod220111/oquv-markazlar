from django.urls import path
from .views import SubjectListView, CenterListView, CenterDetailView, SuggestView

urlpatterns = [
    path("subjects/", SubjectListView.as_view()),
    path("suggest/", SuggestView.as_view()),
    path("centers/", CenterListView.as_view()),
    path("centers/<int:pk>/", CenterDetailView.as_view()),
]