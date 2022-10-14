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
from ..consts import *


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

URL_REVERSE = {
    'post_create': reverse('posts:post_create'),
    'profile': reverse('posts:profile', kwargs={'username': NAME_USER}),
}


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Создаём картинку
        cls.test_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.picture = SimpleUploadedFile(
            name='pic.gif',
            content=cls.test_gif,
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
            URL_REVERSE['post_create'],
            data=form_data,
        )
        self.assertRedirects(
            response, URL_REVERSE['profile'])
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
        # здесь реверс в константу не внести из-за pk,
        # его в константы никак не внести
        response = self.authorized_client.post(
            path=reverse('posts:post_edit', kwargs={'post_id': self.post0.pk}),
            data=form_data
        )
        # здесь реверс в константу не внести из-за pk,
        # его в константы никак не внести
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post0.pk}))
        self.post0.refresh_from_db()
        self.assertEqual(self.post0.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_guest_create_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': POST_TEXT
        }
        response = self.guest_client.post(
            URL_REVERSE['post_create'],
            data=form_data,
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_guest_edit_post(self):
        form_data = {
            'text': 'Новый текст поста'
        }
        # здесь реверс в константу не внести из-за pk,
        # его в константы никак не внести
        response = self.guest_client.post(
            path=reverse('posts:post_edit',
                         kwargs={'post_id': self.post0.pk}),
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
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post0.pk}),
            data=comment_form)
        print(response1.status_code)
        # проверяем доступ неавторизированного пользователя
        self.guest_client = Client()
        response2 = self.guest_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post0.pk}),
            data=comment_form)
        # авторизированного должно перенаправить на детали поста,
        # неавторизированного - на страницу авторизации
        self.assertRedirects(response1,
                             f'/posts/{self.post0.pk}/')
        self.assertRedirects(response2,
                             f'/auth/login/?next='
                             f'/posts/{self.post0.pk}/comment/')