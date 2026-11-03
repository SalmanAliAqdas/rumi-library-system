from django.urls import path

from . import offline, views

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.search, name="search"),
    path("books/<int:pk>/", views.detail, name="detail"),
    path("offline/", offline.shell, name="offline"),
    path("offline/sw.js", offline.service_worker, name="offline_sw"),
    path("catalog/public-snapshot.json", offline.snapshot, name="public_snapshot"),
]
