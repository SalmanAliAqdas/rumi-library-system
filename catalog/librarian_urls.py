from django.urls import path

from . import librarian

app_name = "librarian"
urlpatterns = [
    path("login/", librarian.LibrarianLoginView.as_view(), name="login"),
    path("logout/", librarian.LibrarianLogoutView.as_view(), name="logout"),
    path("", librarian.dashboard, name="dashboard"),
    path("books/", librarian.book_list, name="book_list"),
    path("books/add/", librarian.book_add, name="book_add"),
    path("books/<int:pk>/", librarian.book_detail, name="book_detail"),
    path("books/<int:pk>/edit/", librarian.book_edit, name="book_edit"),
    path("books/<int:pk>/copies/add/", librarian.copy_add, name="copy_add"),
    path("books/<int:pk>/volumes/", librarian.volumes, name="volumes"),
    path("copies/<int:pk>/edit/", librarian.copy_edit, name="copy_edit"),
    path("records/<str:kind>/", librarian.metadata_list, name="metadata_list"),
    path("records/<str:kind>/add/", librarian.metadata_edit, name="metadata_add"),
    path("records/<str:kind>/<int:pk>/edit/", librarian.metadata_edit, name="metadata_edit"),
]
