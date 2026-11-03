from django.db.models.deletion import ProtectedError
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Category, Language
from .templatetags.library_ui import ui


@receiver(pre_delete, sender=Category)
@receiver(pre_delete, sender=Language)
def protect_edition_tags(sender, instance, using, **kwargs):
    referenced = instance.edition_set.using(using).all()
    if referenced.exists():
        raise ProtectedError(ui("referenced"), referenced)
