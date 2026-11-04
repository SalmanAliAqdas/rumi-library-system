"""Read-only transfer verification. Emits counts/digests, never private records."""

import hashlib
import json
import re

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import F

from catalog.models import AccessionSequence, Copy, Loan


class Command(BaseCommand):
    help = "Read-only catalog integrity/count/digest report for private transfer comparison."

    def handle(self, **options):
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            connection.check_constraints()
            accessions = list(Copy.objects.values_list("accession", flat=True))
            if len(accessions) != len(set(accessions)) or any(
                not re.fullmatch(r"RL-\d{6,}", x) for x in accessions
            ):
                raise CommandError("Invalid or duplicate accessions; investigate before transfer.")
            sequence = AccessionSequence.objects.filter(pk=1).first()
            if accessions and (not sequence or sequence.value < max(int(x[3:]) for x in accessions)):
                raise CommandError("Accession sequence is behind inventory.")
            if (
                Loan.objects.filter(due_date__lt=F("issue_date")).exists()
                or Loan.objects.filter(returned_date__lt=F("issue_date")).exists()
            ):
                raise CommandError("Invalid loan date relationships.")
            report = {}
            for model in apps.get_app_config("catalog").get_models():
                if model._meta.model_name in {"submission", "lookupgate"}:
                    continue
                queryset = model.objects.order_by("code" if model._meta.model_name == "language" else "pk")
                payload = json.loads(
                    serializers.serialize(
                        "json", queryset, use_natural_foreign_keys=True, use_natural_primary_keys=True
                    )
                )
                # M2M ordering is not guaranteed across database backends.
                for item in payload:
                    for name, value in item["fields"].items():
                        if isinstance(value, list):
                            item["fields"][name] = sorted(value, key=lambda x: json.dumps(x, sort_keys=True))
                report[model._meta.label_lower] = {
                    "count": len(payload),
                    "sha256": hashlib.sha256(
                        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
                    ).hexdigest(),
                }
            report["visibility"] = {
                "public": Copy.objects.filter(is_public=True).count(),
                "hidden": Copy.objects.filter(is_public=False).count(),
            }
            report["loans"] = {
                "active": Loan.objects.filter(returned_date__isnull=True).count(),
                "available_public": Copy.objects.filter(is_public=True)
                .exclude(pk__in=Loan.objects.filter(returned_date__isnull=True).values("copy_id"))
                .count(),
            }
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
