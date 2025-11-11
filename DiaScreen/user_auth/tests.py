from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .forms import LoginForm, UserRegistrationForm


User = get_user_model()


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "StrongPass123"
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=self.password,
        )

    def test_render_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/login-form.html")
        self.assertIsInstance(response.context["form"], LoginForm)

    def test_redirect_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("home"))

    def test_successful_login(self):
        response = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": self.password},
            follow=True,
        )
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(response.context["user"].is_authenticated)

    def test_login_with_email(self):
        response = self.client.post(
            reverse("login"),
            {"username": "test@example.com", "password": self.password},
        )
        self.assertRedirects(response, reverse("home"))

    def test_login_invalid_credentials(self):
        response = self.client.post(
            reverse("login"),
            {"username": "testuser", "password": "wrong"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["user"].is_authenticated)
        messages = list(response.context["messages"])
        self.assertTrue(
            any("Будь ласка, виправте помилки" in msg.message for msg in messages)
        )


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_render_register_page(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/register-form.html")
        self.assertIsInstance(response.context["form"], UserRegistrationForm)

    def test_redirect_authenticated_user(self):
        user = User.objects.create_user(
            username="exists",
            email="exists@example.com",
            password="Secure12345",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("register"))
        self.assertRedirects(response, reverse("home"))

    def test_successful_registration(self):
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "StrongPass123",
            "password2": "StrongPass123",
            "policy_agreement": True,
        }
        response = self.client.post(reverse("register"), payload, follow=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertTrue(response.context["user"].is_authenticated)

    def test_registration_password_mismatch(self):
        payload = {
            "username": "foo",
            "email": "foo@example.com",
            "password1": "StrongPass123",
            "password2": "Mismatch123",
            "policy_agreement": True,
        }
        response = self.client.post(reverse("register"), payload)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_registration_without_policy_agreement(self):
        payload = {
            "username": "bar",
            "email": "bar@example.com",
            "password1": "StrongPass123",
            "password2": "StrongPass123",
            "policy_agreement": False,
        }
        response = self.client.post(reverse("register"), payload)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("policy_agreement", form.errors)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="logout-user",
            email="logout@example.com",
            password="Logout12345",
        )

    def test_logout_redirects_to_home(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"), follow=True)
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(response.context["user"].is_authenticated)
