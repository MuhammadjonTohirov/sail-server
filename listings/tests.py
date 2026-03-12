from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from accounts.models import Profile
from favorites.models import FavoriteListing
from taxonomy.models import Attribute, Category, Location

from .models import Listing, ListingAttributeValue
from .views.my_listings_view import MyListingsView


class ListingApiTests(APITestCase):
    def setUp(self):
        self.task_index_patcher = patch("listings.signals.task_index_listing.delay", return_value=None)
        self.task_delete_patcher = patch("listings.signals.task_delete_listing.delay", return_value=None)
        self.task_index_patcher.start()
        self.task_delete_patcher.start()
        self.addCleanup(self.task_index_patcher.stop)
        self.addCleanup(self.task_delete_patcher.stop)

        self.User = get_user_model()
        self.seller = self.User.objects.create_user(username="seller", password="pass123")
        self.viewer = self.User.objects.create_user(username="viewer", password="pass123")
        Profile.objects.create(
            user=self.seller,
            phone_e164="+998901112233",
            email="seller@example.com",
            display_name="",
        )
        Profile.objects.create(
            user=self.viewer,
            phone_e164="+998907770000",
            email="viewer@example.com",
            display_name="Viewer",
        )

        self.location = Location.objects.create(
            name="Tashkent",
            slug="tashkent",
            kind=Location.Kind.CITY,
        )
        self.category = Category.objects.create(
            name="Smartphones",
            slug="smartphones",
            level=1,
            is_leaf=True,
        )
        self.attribute = Attribute.objects.create(
            category=self.category,
            key="storage",
            label="Storage",
            type=Attribute.Type.TEXT,
        )

    def _create_listing(self, **kwargs) -> Listing:
        defaults = {
            "user": self.seller,
            "category": self.category,
            "location": self.location,
            "title": "iPhone 15",
            "description": "Factory sealed",
            "price_amount": Decimal("1200.00"),
            "price_currency": "USD",
            "status": Listing.Status.ACTIVE,
            "contact_name": "Seller Contact",
            "contact_email": "seller-listing@example.com",
            "contact_phone": "+998901112233",
            "contact_phone_masked": "+998901112233",
        }
        defaults.update(kwargs)
        return Listing.objects.create(**defaults)

    def test_public_detail_hides_private_contact_and_recomputes_mask(self):
        listing = self._create_listing()

        response = self.client.get(reverse("listing-detail", kwargs={"pk": listing.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contact_phone"], "")
        self.assertEqual(response.data["contact_email"], "")
        self.assertEqual(response.data["contact_phone_masked"], "+998****33")
        self.assertEqual(response.data["seller"]["name"], "Seller Contact")

        self.client.force_authenticate(user=self.seller)
        owner_response = self.client.get(reverse("listing-detail", kwargs={"pk": listing.id}))
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(owner_response.data["contact_phone"], "+998901112233")
        self.assertEqual(owner_response.data["contact_email"], "seller-listing@example.com")

    def test_public_detail_blocks_drafts_but_owner_can_still_fetch(self):
        listing = self._create_listing(status=Listing.Status.DRAFT, title="Draft listing")

        anonymous_response = self.client.get(reverse("listing-detail", kwargs={"pk": listing.id}))
        self.assertEqual(anonymous_response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.seller)
        owner_response = self.client.get(reverse("listing-detail", kwargs={"pk": listing.id}))
        self.assertEqual(owner_response.status_code, status.HTTP_200_OK)
        self.assertEqual(owner_response.data["status"], Listing.Status.DRAFT)

    def test_raw_update_recomputes_contact_mask(self):
        listing = self._create_listing(contact_phone="+998901110000", contact_phone_masked="+998****00")
        self.client.force_authenticate(user=self.seller)

        response = self.client.patch(
            reverse("listing-update-raw", kwargs={"pk": listing.id}),
            {"contact_phone": "+998907654321"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertEqual(listing.contact_phone, "+998907654321")
        self.assertEqual(listing.contact_phone_masked, "+998****21")
        self.assertEqual(response.data["contact_phone_masked"], "+998****21")

    def test_reveal_contact_returns_private_data_and_tracks_interest(self):
        listing = self._create_listing()

        response = self.client.post(reverse("listing-reveal-contact", kwargs={"pk": listing.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contact_phone"], "+998901112233")
        self.assertEqual(response.data["contact_email"], "seller-listing@example.com")
        self.assertEqual(response.data["contact_name"], "Seller Contact")
        self.assertTrue(response.data["tracked"])
        listing.refresh_from_db()
        self.assertEqual(listing.interest_count, 1)

    def test_owner_reveal_contact_does_not_increment_interest(self):
        listing = self._create_listing()
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(reverse("listing-reveal-contact", kwargs={"pk": listing.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["tracked"])
        listing.refresh_from_db()
        self.assertEqual(listing.interest_count, 0)

    def test_signal_dispatch_falls_back_when_broker_is_unavailable(self):
        with patch("listings.signals.task_index_listing.delay", side_effect=RuntimeError("broker down")), patch(
            "listings.signals.index_listing"
        ) as index_mock:
            with self.captureOnCommitCallbacks(execute=True):
                listing = self._create_listing(title="Broker fallback create")
            index_mock.assert_called_once_with(listing.id)

        with patch("listings.signals.task_delete_listing.delay", side_effect=RuntimeError("broker down")), patch(
            "listings.signals.delete_listing"
        ) as delete_mock:
            listing_id = listing.id
            with self.captureOnCommitCallbacks(execute=True):
                listing.delete()
            delete_mock.assert_called_once_with(listing_id)

    def test_my_listings_query_count_stays_bounded(self):
        listings = [
            self._create_listing(title=f"Phone {idx}", price_amount=Decimal("1000.00") + idx)
            for idx in range(3)
        ]
        for idx, listing in enumerate(listings):
            ListingAttributeValue.objects.create(
                listing=listing,
                attribute=self.attribute,
                value_text=f"{128 + idx}GB",
            )
            FavoriteListing.objects.create(user=self.viewer, listing=listing)

        factory = APIRequestFactory()
        request = factory.get(reverse("my-listings"))
        force_authenticate(request, user=self.seller)

        with CaptureQueriesContext(connection) as ctx:
            response = MyListingsView.as_view()(request)
            response.render()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(ctx.captured_queries), 12)
