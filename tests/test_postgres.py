"""These tests require a disposable PostgreSQL test database before launch."""

from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from catalog.models import Copy, Edition, Shelf


@skipUnless(connection.vendor == "postgresql", "PostgreSQL concurrency must be verified before production")
class PostgresAccessionTests(TransactionTestCase):
    def test_concurrent_accessions_are_unique(self):
        edition = Edition.objects.create(title="Concurrency fixture")
        shelf = Shelf.objects.create(label="Fixture")

        def create_copy(_):
            close_old_connections()
            try:
                return Copy.objects.create(edition_id=edition.pk, shelf_id=shelf.pk).accession
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=4) as pool:
            accessions = list(pool.map(create_copy, range(12)))
        self.assertEqual(len(set(accessions)), 12)
        self.assertEqual(Copy.objects.count(), 12)
