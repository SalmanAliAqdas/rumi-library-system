"""These tests require a disposable PostgreSQL test database before launch."""

from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from catalog.models import Copy, Edition, Shelf


@skipUnless(connection.vendor == "postgresql", "PostgreSQL lookup gate requires a disposable database")
class PostgresLookupTests(TransactionTestCase):
    def test_shared_reservation_allows_only_one_concurrent_request(self):
        from threading import Barrier

        from catalog.metadata import LookupError, reserve_request
        from catalog.models import LookupGate

        LookupGate.objects.create(pk=1)
        barrier = Barrier(2)

        def reserve():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    reserve_request()
                    return True
                except LookupError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: reserve(), range(2)))
        self.assertEqual(sorted(results), [False, True])


@skipUnless(
    connection.vendor == "postgresql", "PostgreSQL lending concurrency requires a disposable database"
)
class PostgresLendingTests(TransactionTestCase):
    def test_competing_issues_and_same_token_retries(self):
        from threading import Barrier

        from django.contrib.auth import get_user_model
        from django.test import Client
        from django.utils import timezone

        from catalog.models import Loan
        from catalog.workflows import issue_token

        user = get_user_model().objects.create_superuser("concurrent-lending-fixture")
        edition = Edition.objects.create(title="Concurrency fixture")
        shelf = Shelf.objects.create(label="Concurrency shelf")
        copy = Copy.objects.create(edition=edition, shelf=shelf)
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(user)

        def race(tokens):
            barrier = Barrier(2)

            def submit(index):
                close_old_connections()
                try:
                    barrier.wait(timeout=10)
                    return (
                        clients[index]
                        .post(
                            "/librarian/loans/issue/",
                            {
                                "copy": copy.pk,
                                "borrower_name": "Concurrency fixture",
                                "issue_date": timezone.localdate(),
                                "token": tokens[index],
                            },
                        )
                        .status_code
                    )
                finally:
                    close_old_connections()

            with ThreadPoolExecutor(max_workers=2) as pool:
                return sorted(pool.map(submit, range(2)))

        self.assertEqual(race([issue_token(user, "loan:issue") for _ in range(2)]), [200, 302])
        self.assertEqual(Loan.objects.filter(returned_date__isnull=True).count(), 1)
        Loan.objects.update(returned_date=timezone.localdate())
        token = issue_token(user, "loan:issue")
        self.assertEqual(race([token, token]), [302, 302])
        self.assertEqual(Loan.objects.count(), 2)
        active = Loan.objects.get(returned_date__isnull=True)

        def return_copy(index):
            close_old_connections()
            try:
                return clients[index].post(f"/librarian/loans/{active.pk}/return/").status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(return_copy, range(2))), [302, 302])
        self.assertFalse(Loan.objects.filter(returned_date__isnull=True).exists())
        self.assertEqual(Loan.objects.count(), 2)


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
