from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class LoginTest(TestCase):
    def setUp(self):
        # Create users with different roles
        self.faculty_user = CustomUser.objects.create_user(
            username='faculty_user',
            password='faculty_password',
            role='Faculty',
            employee_id='EMP001'
        )
        self.admin_user = CustomUser.objects.create_user(
            username='admin_user',
            password='admin_password',
            role='Admin',
            employee_id='EMP002'
        )
        self.superuser = CustomUser.objects.create_superuser(
            username='super_user',
            password='super_password',
            role='Superuser',
            employee_id='EMP003'
        )

    def test_valid_login_redirect_faculty(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'faculty_user',
            'password': 'faculty_password'
        })
        self.assertEqual(response.status_code, 302)  # Check initial redirect
        self.assertEqual(response.url, reverse('users:redirect_view'))  # Check URL of the first redirect

        # Follow the redirect
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:faculty_dashboard'))  # Final redirect to dashboard

    def test_valid_login_redirect_admin(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'admin_user',
            'password': 'admin_password'
        })
        self.assertEqual(response.status_code, 302)  # Check initial redirect
        self.assertEqual(response.url, reverse('users:redirect_view'))  # Check URL of the first redirect

        # Follow the redirect
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:admin_dashboard'))  # Final redirect to dashboard

    def test_valid_login_redirect_superuser(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'super_user',
            'password': 'super_password'
        })
        self.assertEqual(response.status_code, 302)  # Check initial redirect
        self.assertEqual(response.url, reverse('users:redirect_view'))  # Check URL of the first redirect

        # Follow the redirect
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:superuser_dashboard'))  # Final redirect to dashboard

    def test_invalid_login(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'invalid_user',
            'password': 'invalid_password'
        })
        self.assertContains(response, "Please enter a correct username and password.")


class ProfileAccessTest(TestCase):
    def setUp(self):
        self.faculty_user = CustomUser.objects.create_user(
            username='faculty_user',
            password='faculty_password',
            role='Faculty',
            employee_id='EMP001'
        )
        self.admin_user = CustomUser.objects.create_user(
            username='admin_user',
            password='admin_password',
            role='Admin',
            employee_id='EMP002'
        )

    def test_faculty_access_own_profile(self):
        self.client.login(username='faculty_user', password='faculty_password')
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "faculty_user")

    def test_faculty_access_admin_profile(self):
        self.client.login(username='faculty_user', password='faculty_password')
        response = self.client.get(reverse('users:profile'))
        self.assertNotContains(response, "admin_user")


class SuperuserPermissionsTest(TestCase):
    def setUp(self):
        self.superuser = CustomUser.objects.create_superuser(
            username='super_user',
            password='super_password',
            role='Superuser',
            employee_id='EMP003'
        )

    def test_superuser_can_add_user(self):
        self.client.login(username='super_user', password='super_password')
        response = self.client.post(reverse('admin:users_customuser_add'), {
            'username': 'new_user',
            'password1': 'newpassword',
            'password2': 'newpassword',
            'role': 'Faculty',
            'employee_id': 'EMP004'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(CustomUser.objects.filter(username='new_user').exists())


class DashboardContentTest(TestCase):
    def setUp(self):
        self.faculty_user = CustomUser.objects.create_user(
            username='faculty_user',
            password='faculty_password',
            role='Faculty',
            employee_id='EMP001'
        )
        self.admin_user = CustomUser.objects.create_user(
            username='admin_user',
            password='admin_password',
            role='Admin',
            employee_id='EMP002'
        )

    def test_faculty_dashboard_content(self):
        self.client.login(username='faculty_user', password='faculty_password')
        response = self.client.get(reverse('users:faculty_dashboard'))
        self.assertContains(response, "Welcome, faculty_user (Faculty)")
        self.assertContains(response, "Create Minute")
        self.assertContains(response, "Track Minute")
        self.assertContains(response, "Archive")

    def test_admin_dashboard_content(self):
        self.client.login(username='admin_user', password='admin_password')
        response = self.client.get(reverse('users:admin_dashboard'))
        self.assertContains(response, "Welcome, admin_user (Admin)")
        self.assertContains(response, "Manage Approvals")
        self.assertContains(response, "View Department Archives")


class AuthenticationTest(TestCase):
    def setUp(self):
        self.faculty_user = CustomUser.objects.create_user(
            username='faculty_user',
            password='faculty_password',
            role='Faculty',
            employee_id='EMP001'
        )

    def test_unauthenticated_access(self):
        response = self.client.get(reverse('users:faculty_dashboard'))
        expected_redirect = f"{reverse('users:login')}?next={reverse('users:faculty_dashboard')}"
        self.assertRedirects(response, expected_redirect)  # Test should pass now

    def test_logout(self):
        # Log in the user
        self.client.login(username='faculty_user', password='faculty_password')

        # Test logout using POST method
        response = self.client.post(reverse('users:logout'))
        self.assertRedirects(response, reverse('users:login'))
