from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.search, name="search"),
    path("books/<int:pk>/", views.detail, name="detail"),
]
