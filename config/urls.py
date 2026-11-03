from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("librarian/", include("catalog.librarian_urls")),
    path("", include("catalog.urls")),
]

handler403 = "catalog.views.permission_denied"
