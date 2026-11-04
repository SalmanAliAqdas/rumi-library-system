from django.urls import path

from . import offline, seo, views

urlpatterns = [
    path("sitemap.xml", seo.sitemap, name="sitemap"),
    path("robots.txt", seo.robots, name="robots"),
    path("health/", seo.health, name="health"),
    path("", views.home, name="home"),
    path("books/", views.search, name="search"),
    path("books/<int:pk>/", views.detail, name="detail"),
    path("copies/<str:accession>/", views.copy_detail, name="copy_detail"),
    path("offline/", offline.shell, name="offline"),
    path("offline/sw.js", offline.service_worker, name="offline_sw"),
    path("catalog/public-snapshot.json", offline.snapshot, name="public_snapshot"),
]
