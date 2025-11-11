from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from PIL import Image

from .models import Article


User = get_user_model()


class BlogBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_group = Group.objects.create(name='Administrators')
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPass123',
        )
        cls.admin_user.groups.add(cls.admin_group)

        cls.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='Regular12345',
        )

        cls.article = Article.objects.create(
            article_name='Test Article',
            article_short_name='TA',
            article_author='Author',
            article_description='Short description',
            article_img=cls._create_test_image(),
            article_text='Paragraph 1.\nParagraph 2.',
        )

    @staticmethod
    def _create_test_image():
        image_io = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(image_io, format='PNG')
        image_io.seek(0)
        return SimpleUploadedFile('test.png', image_io.read(), content_type='image/png')


class InformationPanelTests(BlogBaseTestCase):
    def setUp(self):
        self.client = Client()

    def test_information_panel_for_anonymous(self):
        response = self.client.get(reverse('information'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/info_panel.html')
        self.assertIn('article_list', response.context)
        self.assertFalse(response.context['is_admin'])
        self.assertNotIn('article_creation_form', response.context)

    def test_information_panel_for_admin_get(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('information'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_admin'])
        self.assertIn('article_creation_form', response.context)

    def test_information_panel_create_article_admin(self):
        self.client.force_login(self.admin_user)
        payload = {
            'article_name': 'Another Article',
            'article_short_name': 'AA',
            'article_author': 'Someone',
            'article_description': 'Desc',
            'article_text': 'Text body',
        }
        payload_files = {
            'article_img': self._create_test_image(),
        }
        response = self.client.post(
            reverse('information'), data={**payload, **payload_files}, follow=True
        )
        self.assertRedirects(response, reverse('information'))
        self.assertTrue(Article.objects.filter(article_name='Another Article').exists())

    def test_information_panel_create_article_non_admin_forbidden(self):
        self.client.force_login(self.regular_user)
        response = self.client.post(
            reverse('information'), data={'article_name': 'Should Fail'}
        )
        self.assertEqual(response.status_code, 403)


class ArticleDetailTests(BlogBaseTestCase):
    def setUp(self):
        self.client = Client()

    def test_article_detail_anonymous(self):
        response = self.client.get(reverse('article_detail', args=[self.article.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/article_detail.html')
        self.assertFalse(response.context['is_admin'])
        self.assertIn('paragraphs', response.context)
        self.assertEqual(response.context['paragraphs'], ['Paragraph 1.', 'Paragraph 2.'])

    def test_article_detail_admin_has_form(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('article_detail', args=[self.article.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_admin'])
        self.assertIn('article_form', response.context)


class DeleteArticleTests(BlogBaseTestCase):
    def setUp(self):
        self.client = Client()

    def test_delete_article_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('delete_article', args=[self.article.pk]), follow=True
        )
        self.assertRedirects(response, reverse('information'))
        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())

    def test_delete_article_non_admin_forbidden(self):
        self.client.force_login(self.regular_user)
        response = self.client.post(reverse('delete_article', args=[self.article.pk]))
        self.assertEqual(response.status_code, 403)


class EditArticleTests(BlogBaseTestCase):
    def setUp(self):
        self.client = Client()

    def test_edit_article_get_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('edit_article', args=[self.article.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/edit_article.html')
        self.assertTrue(response.context['is_admin'])

    def test_edit_article_post_admin(self):
        self.client.force_login(self.admin_user)
        payload = {
            'article_name': 'Updated Article',
            'article_short_name': 'TA',
            'article_author': 'Author',
            'article_description': 'Short description',
            'article_text': 'Updated text',
        }
        response = self.client.post(
            reverse('edit_article', args=[self.article.pk]),
            data={**payload, 'article_img': self._create_test_image()},
            follow=True,
        )
        self.assertRedirects(response, reverse('article_detail', args=[self.article.pk]))
        self.article.refresh_from_db()
        self.assertEqual(self.article.article_name, 'Updated Article')

    def test_edit_article_non_admin_forbidden(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse('edit_article', args=[self.article.pk]))
        self.assertEqual(response.status_code, 403)
