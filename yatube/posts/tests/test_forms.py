from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from datetime import datetime as dt
from http import HTTPStatus
import tempfile
import shutil
from PIL import Image, ImageChops

from ..forms import PostForm
from ..models import Group, Post, User
from .consts import (NAME_USER,
                     NAME_GROUP,
                     SLUG,
                     POST_TEXT,
                     TEST_GIF)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picture = SimpleUploadedFile(
            name='pic.gif',
            content=TEST_GIF,
            content_type='image/gif')

        # Создаём автора
        cls.my_author = User.objects.create_user(username=NAME_USER)

        # Создаём группу
        cls.group = Group.objects.create(
            title=NAME_GROUP,
            slug=SLUG
        )
        # Создаём пост
        cls.post0 = Post.objects.create(
            text=POST_TEXT,
            author=cls.my_author,
            pub_date=dt.now(),
            group=cls.group
        )

        # Создаём форму
        cls.form = PostForm

        cls.url_reverse = {
            'post_create': reverse(
                'posts:post_create'),
            'profile': reverse(
                'posts:profile', kwargs={'username': NAME_USER}),
            'post_detail': reverse(
                'posts:post_detail', kwargs={'post_id': cls.post0.pk}),
            'post_edit': reverse(
                'posts:post_edit', kwargs={'post_id': cls.post0.pk}),
            'add_comment': reverse(
                'posts:add_comment', kwargs={'post_id': cls.post0.pk})
        }

    def setUp(self):
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.my_author)
        # Создаём неавторизированый клиент
        self.guest_client = Client()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создаёт запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': POST_TEXT,
            'group': self.group.pk,
            'image': self.picture
        }
        response = self.authorized_client.post(
            self.url_reverse['post_create'],
            data=form_data,
        )
        self.assertRedirects(
            response, self.url_reverse['profile'])
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Post.objects.count(), posts_count + 1)

        check_post = Post.objects.first()
        self.assertEqual(check_post.text, form_data['text'])
        self.assertEqual(check_post.group.pk, form_data['group'])
        actual_pic = Image.open(check_post.image)
        expected_pic = Image.open(self.picture)
        result = ImageChops.difference(actual_pic, expected_pic).getbbox()
        self.assertEqual(None, result)

    def test_edit_post(self):
        """Валидная форма редактирования обновляет запись в Post."""
        form_data = {
            'text': 'Новый текст поста'
        }
        response = self.authorized_client.post(
            path=self.url_reverse['post_edit'],
            data=form_data
        )
        self.assertRedirects(
            response,
            self.url_reverse['post_detail'])
        self.post0.refresh_from_db()
        self.assertEqual(self.post0.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_guest_create_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': POST_TEXT
        }
        response = self.guest_client.post(
            self.url_reverse['post_create'],
            data=form_data,
        )
        self.assertRedirects(
            response, '/auth/login/?next=/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_guest_edit_post(self):
        form_data = {
            'text': 'Новый текст поста'
        }
        response = self.guest_client.post(
            path=self.url_reverse['post_edit'],
            data=form_data
        )
        # здесь реверс в константу не внести из-за pk,
        # его в константы никак не внести
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post0.pk}/edit/')
        self.post0.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_authorized_comments(self):
        """Комментировать посты может только авторизованный пользователь"""
        # проверяем доступ авторизированного пользователя
        comment_form = {'text': 'Текст комментария'}
        response1 = self.authorized_client.post(
            self.url_reverse['add_comment'],
            data=comment_form)
        # проверяем доступ неавторизированного пользователя
        self.guest_client = Client()
        response2 = self.guest_client.post(
            self.url_reverse['add_comment'],
            data=comment_form)
        # авторизированного должно перенаправить на детали поста,
        # неавторизированного - на страницу авторизации
        self.assertRedirects(response1,
                             f'/posts/{self.post0.pk}/')
        self.assertRedirects(response2,
                             f'/auth/login/?next='
                             f'/posts/{self.post0.pk}/comment/')
