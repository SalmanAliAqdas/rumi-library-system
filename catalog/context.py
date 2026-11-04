from .models import Edition, LibrarySettings


def library_context(request):
    return {
        "library": LibrarySettings.objects.first() or LibrarySettings(),
        "demo_mode": Edition.objects.filter(is_demo=True, copies__is_public=True).exists(),
        "display_mode": request.GET.get("display") == "1",
    }
