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


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


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
        cls.my_author = User.objects.create_user(username='IamAuthor')

        # Создаём группу
        cls.group = Group.objects.create(
            title='IamGroup',
            slug='IamGroupSlug'
        )
        # Создаём пост
        cls.post0 = Post.objects.create(
            text='Тестовый текст поста',
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создаёт запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Здесь текст',
            'group': self.group.pk,
            # sprint 6
            'image': self.picture
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': self.my_author.username}))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Post.objects.count(), posts_count + 1)

        check_post = Post.objects.first()
        self.assertEqual(check_post.text, form_data['text'])
        self.assertEqual(check_post.group.pk, form_data['group'])
        # sprint 6
        actual_pic = Image.open(check_post.image)
        expected_pic = Image.open(self.picture)
        result = ImageChops.difference(actual_pic, expected_pic).getbbox()
        self.assertEqual(None, result)

    def test_edit_post(self):
        """Валидная форма редактирования обновляет запись в Post."""
        pk = PostsFormTests.post0.pk
        form_data = {
            'text': 'Новый текст поста'
        }
        response = self.authorized_client.post(
            path=reverse('posts:post_edit', kwargs={'post_id': pk}),
            data=form_data
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail', kwargs={'post_id': pk}))
        self.post0.refresh_from_db()
        self.assertEqual(self.post0.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
