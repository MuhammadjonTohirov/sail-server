from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Profile
from chat.models import ChatMessage, ChatThread
from taxonomy.models import Category, Location
from listings.models import Listing


@override_settings(
    CHAT_ATTACHMENT_ALLOWED_URL_PREFIXES=["https://cdn.example.com/"],
    CHAT_MAX_ATTACHMENTS_PER_MESSAGE=5,
)
class ChatApiTests(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.seller = self.User.objects.create_user(username="seller", password="pass123")
        self.buyer = self.User.objects.create_user(username="buyer", password="pass123")
        Profile.objects.create(user=self.seller, phone_e164="+998901112233", display_name="Seller")
        Profile.objects.create(user=self.buyer, phone_e164="+998998887766", display_name="Buyer")

        self.location = Location.objects.create(
            name="Tashkent",
            slug="tashkent",
            kind=Location.Kind.CITY,
        )
        self.category = Category.objects.create(name="Electronics", slug="electronics", level=1, is_leaf=True)
        self.listing = Listing.objects.create(
            user=self.seller,
            category=self.category,
            location=self.location,
            title="Camera",
            description="Great camera",
            price_amount=Decimal("21.00"),
            price_currency="USD",
            contact_phone_masked="+998****23",
        )

    def _create_thread(self, payload: dict[str, Any] | None = None, expected_status: int = status.HTTP_201_CREATED) -> dict[str, Any]:
        url = reverse("chat-threads-list")
        payload = payload or {"listing_id": self.listing.id, "message": "Hello there!"}
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, expected_status)
        return response.json()

    def test_create_thread_and_send_message(self):
        with patch("chat.services.schedule_new_message_notifications") as notify_mock:
            data = self._create_thread()
            notify_mock.assert_called_once()
            thread_id = data["id"]
            self.assertEqual(ChatThread.objects.count(), 1)
            self.assertEqual(ChatMessage.objects.count(), 1)

            notify_mock.reset_mock()
            url = reverse("chat-threads-list")
            response = self.client.post(
                url,
                {"listing_id": self.listing.id, "message": "Second message"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(ChatThread.objects.count(), 1)
            self.assertEqual(ChatMessage.objects.count(), 2)
            notify_mock.assert_called_once()

        # Seller can read messages and mark as read
        self.client.force_authenticate(user=self.seller)
        messages_url = reverse("chat-threads-messages", kwargs={"id": thread_id})
        messages_response = self.client.get(messages_url)
        self.assertEqual(messages_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(messages_response.json()["messages"]), 2)

        last_message_id = messages_response.json()["messages"][-1]["id"]
        read_url = reverse("chat-threads-read", kwargs={"id": thread_id})
        mark_read_response = self.client.post(read_url, {"message_id": last_message_id}, format="json")
        self.assertEqual(mark_read_response.status_code, status.HTTP_200_OK)
        self.assertEqual(mark_read_response.json()["unread_count"], 0)

    def test_archive_and_delete_thread(self):
        data = self._create_thread()
        thread_id = data["id"]

        self.client.force_authenticate(user=self.buyer)
        archive_url = reverse("chat-threads-archive", kwargs={"id": thread_id})
        response = self.client.post(archive_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["is_archived"])

        unarchive_url = reverse("chat-threads-unarchive", kwargs={"id": thread_id})
        response = self.client.post(unarchive_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["is_archived"])

        delete_url = reverse("chat-threads-detail", kwargs={"id": thread_id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        list_url = reverse("chat-threads-list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_create_thread_with_attachments(self):
        payload = {
            "listing_id": self.listing.id,
            "attachments": [
                {
                    "type": "image",
                    "url": "https://cdn.example.com/img1.jpg",
                    "name": "photo.jpg",
                    "width": 800,
                    "height": 600,
                }
            ],
            "message": "   text with spaces   ",
        }
        with patch("chat.services.schedule_new_message_notifications"):
            data = self._create_thread(payload)
        thread_id = data["id"]
        message = ChatMessage.objects.get(thread_id=thread_id)
        self.assertEqual(message.body, "text with spaces")
        self.assertEqual(message.attachments[0]["type"], "image")

    def test_attachment_validation_errors(self):
        # Missing URL should fail
        payload = {
            "listing_id": self.listing.id,
            "attachments": [{"type": "file", "name": "doc"}],
        }
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(reverse("chat-threads-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Too many attachments should fail
        many_attachments = [
            {"type": "file", "url": f"https://cdn.example.com/{i}.pdf", "name": f"file-{i}"}
            for i in range(6)
        ]
        payload = {"listing_id": self.listing.id, "attachments": many_attachments}
        response = self.client.post(reverse("chat-threads-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Disallow external domains
        payload = {
            "listing_id": self.listing.id,
            "attachments": [
                {
                    "type": "file",
                    "url": "https://malicious.example.com/file.pdf",
                    "name": "bad",
                }
            ],
        }
        response = self.client.post(reverse("chat-threads-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_relative_attachment_url_allowed(self):
        payload = {
            "listing_id": self.listing.id,
            "attachments": [
                {"type": "file", "url": "/media/uploads/doc.pdf", "name": "doc.pdf"}
            ],
        }
        with patch("chat.services.schedule_new_message_notifications"):
            data = self._create_thread(payload)
        thread_id = data["id"]
        message = ChatMessage.objects.get(thread_id=thread_id)
        self.assertEqual(message.attachments[0]["url"], "/media/uploads/doc.pdf")

    def test_upload_attachment_endpoint(self):
        data = self._create_thread()
        thread_id = data["id"]
        self.client.force_authenticate(user=self.buyer)
        upload_url = reverse("chat-thread-attachments", kwargs={"id": thread_id})
        doc = SimpleUploadedFile("note.txt", b"hello world", content_type="text/plain")
        response = self.client.post(upload_url, {"file": doc}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()
        self.assertEqual(payload["name"], "note.txt")
        self.assertEqual(payload["size"], len(b"hello world"))
        self.assertEqual(payload["type"], "file")
