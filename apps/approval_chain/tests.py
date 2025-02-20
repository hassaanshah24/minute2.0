from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import ApprovalChain, Approver
from apps.minute.models import Minute

User = get_user_model()


class ApprovalChainModelTest(TestCase):
    """
    Test the ApprovalChain and Approver models.
    """

    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password1')
        self.user2 = User.objects.create_user(username='user2', password='password2')

    def test_create_approval_chain(self):
        """
        Ensure an approval chain can be created.
        """
        chain = ApprovalChain.objects.create(name="Test Chain", created_by=self.user1)
        self.assertEqual(ApprovalChain.objects.count(), 1)
        self.assertEqual(chain.name, "Test Chain")

    def test_add_approver(self):
        """
        Ensure approvers can be added to an approval chain.
        """
        chain = ApprovalChain.objects.create(name="Test Chain", created_by=self.user1)
        approver = Approver.objects.create(approval_chain=chain, user=self.user2, order=1)
        self.assertEqual(Approver.objects.count(), 1)
        self.assertEqual(approver.order, 1)

    def test_duplicate_order_validation(self):
        """
        Ensure duplicate order in the same chain raises an error.
        """
        chain = ApprovalChain.objects.create(name="Test Chain", created_by=self.user1)
        Approver.objects.create(approval_chain=chain, user=self.user2, order=1)
        with self.assertRaises(Exception):
            Approver.objects.create(approval_chain=chain, user=self.user1, order=1)


class ApprovalChainViewTest(TestCase):
    """
    Test the views in the Approval Chain app.
    """

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='password1')
        self.user2 = User.objects.create_user(username='user2', password='password2')
        self.client.login(username='user1', password='password1')
        self.minute = Minute.objects.create(
            title="Test Minute",
            description="Test Description",
            created_by=self.user1
        )

    def test_create_approval_chain_view(self):
        """
        Test creating an approval chain through the view.
        """
        response = self.client.post(reverse('approval_chain:create'), {
            'chain_name': 'Chain Test',
            'approvers[]': [self.user1.id, self.user2.id],
            'order[]': [1, 2],
            'minute_id': self.minute.id,
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(ApprovalChain.objects.count(), 1)
        self.assertEqual(Approver.objects.count(), 2)

    def test_missing_chain_name(self):
        """
        Test error handling when chain name is missing.
        """
        response = self.client.post(reverse('approval_chain:create'), {
            'approvers[]': [self.user1.id],
            'order[]': [1],
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Approval Chain Name is required!", response.json().get('error'))

    def test_link_chain_to_minute(self):
        """
        Test linking an approval chain to a minute.
        """
        chain = ApprovalChain.objects.create(name="Chain Test", created_by=self.user1)
        response = self.client.post(reverse('approval_chain:create'), {
            'chain_name': chain.name,
            'approvers[]': [self.user1.id],
            'order[]': [1],
            'minute_id': self.minute.id,
        })
        self.minute.refresh_from_db()
        self.assertEqual(self.minute.approval_chain, chain)
