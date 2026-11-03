import uuid

from django.core import signing
from django.db import IntegrityError, transaction

from .forms import ROLE_FIELDS
from .models import Contribution, Copy, Submission
from .templatetags.library_ui import ui

SALT = "rumi-library-create-v1"


def issue_token(user, action):
    return signing.dumps({"nonce": str(uuid.uuid4()), "user": user.pk, "action": action}, salt=SALT)


def validate_token(form, user, action):
    try:
        payload = signing.loads(form.cleaned_data.get("token", ""), salt=SALT, max_age=86400)
        nonce = uuid.UUID(payload["nonce"])
        if payload["user"] != user.pk or payload["action"] != action:
            raise ValueError
        return nonce
    except (signing.BadSignature, ValueError, TypeError, KeyError):
        form.add_error(None, ui("expired_form"))
        return None


def create_once(user, action, token, operation):
    """Unique receipt and all writes commit together; retries return the receipt."""
    try:
        with transaction.atomic():
            receipt = Submission.objects.create(token=token, user=user, action=action)
            edition, copies = operation()
            receipt.edition = edition
            receipt.accessions = [copy.accession for copy in copies]
            receipt.save(update_fields=["edition", "accessions"])
        return receipt, True
    except IntegrityError:
        receipt = Submission.objects.filter(token=token, user=user, action=action).first()
        if receipt is None:
            raise
        return receipt, False


def save_credits(edition, form):
    desired = {
        (person.pk, role) for field, role in ROLE_FIELDS.items() for person in form.cleaned_data[field]
    }
    for credit in edition.credits.all():
        pair = (credit.contributor_id, credit.role)
        if pair in desired:
            desired.remove(pair)
        else:
            credit.delete()
    for contributor_id, role in desired:
        Contribution.objects.create(edition=edition, contributor_id=contributor_id, role=role)


def save_new_edition(form, copy_form):
    edition = form.save()
    save_credits(edition, form)
    copy = copy_form.save(commit=False)
    copy.edition = edition
    copy.save()
    return edition, [copy]


def create_copies(edition, shelf, labels, is_public):
    return edition, [
        Copy.objects.create(edition=edition, shelf=shelf, volume=label, is_public=is_public)
        for label in labels
    ]
