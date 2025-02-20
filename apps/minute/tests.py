from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.minute.models import Minute
from apps.approval_chain.models import ApprovalChain

User = get_user_model()

class MinuteFlowTestCase(TestCase):
    def setUp(self):
        """
        Set up test data for the minute creation flow.
        """
        # Create test users
        self.user = User.objects.create_user(
            username="hassaan",
            email="hassaan@example.com",
            password="testpassword",
            role="Faculty",
        )

        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpassword",
        )

        # Log in as the faculty user
        self.client = Client()
        self.client.login(username="hassaan", password="testpassword")

    def test_create_draft_and_submit(self):
        create_url = reverse("minute:create")
        draft_data = {
            "title": "Test Minute",
            "subject": "Test Subject",
            "description": "Draft Description",
            "approval_chain": "",  # Simulate saving as draft
            "action": "draft",  # Ensure 'action' aligns with the view logic
        }

        # Step 1: Create a draft
        response = self.client.post(create_url, draft_data)
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Content: {response.content.decode()}")

        self.assertEqual(response.status_code, 302, "Expected redirect after draft creation.")

        # Fetch the created minute
        minute = Minute.objects.first()
        self.assertIsNotNone(minute, "Draft minute was not created.")
        self.assertEqual(minute.title, "Test Minute")
        self.assertEqual(minute.status, "Draft")

        # Step 2: Submit the minute with approval chain
        submit_data = {
            "title": "Test Minute",
            "subject": "Test Subject",
            "description": "Updated Description",
            "approval_chain": "1",  # Use a valid approval chain ID
            "action": "submit",
        }
        response = self.client.post(create_url + f"?minute_id={minute.id}", submit_data)
        print(f"Submit Response Status Code: {response.status_code}")
        print(f"Submit Response Content: {response.content.decode()}")

        self.assertEqual(response.status_code, 302, "Expected redirect after submission.")

        # Verify status update
        minute.refresh_from_db()
        self.assertEqual(minute.status, "Submitted")
