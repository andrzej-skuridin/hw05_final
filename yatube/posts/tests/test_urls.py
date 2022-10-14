from django.test import TestCase, Client

from datetime import datetime as dt
from http import HTTPStatus

from ..models import Group, Post, User
from ..consts import *


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём группу
        cls.group = Group.objects.create(
            title=NAME_GROUP,
            slug=SLUG)
        # Создаём пост (внимание на то, что тут внутри ещё и автор воздаётся!)
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=User.objects.create_user(username=NAME_USER),
            pub_date=dt.now())
        cls.dict_access = {
            '/': 'all',
            '/group/IamGroupSlug/': 'all',
            '/profile/IamTester/': 'all',
            f'/posts/{cls.post.pk}/': 'all',
            f'/posts/{cls.post.pk}/edit/': 'author',
            '/create/': 'authorized'
        }
        cls.dict_addresses_templates = {
            '/': 'posts/index.html',
            '/group/IamGroupSlug/': 'posts/group_list.html',
            '/profile/IamTester/': 'posts/profile.html',
            f'/posts/{cls.post.pk}/': 'posts/post_detail.html',
            f'/posts/{cls.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html'
        }

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()

        # Создаем авторизированный клиент-тестер
        self.authorized_client = Client()
        self.user = User.objects.create_user(username='IamTester')
        self.authorized_client.force_login(self.user)

        # Создаём авторизированного автора, чтобы проверять редактирование
        self.authorized_author = Client()
        self.authorized_author.force_login(self.post.author)

    def test_general_access(self):
        """Проверка доступа неавторизированного пользователя/
        проверка доступа к общедоступным страницам"""
        response = self.guest_client.get('/fake_page/')
        error_info = 'Обнаружилась несуществующая страница'
        self.assertEqual(response.status_code,
                         HTTPStatus.NOT_FOUND, error_info)
        for address, access in self.dict_access.items():
            if access == 'all':
                with self.subTest(address=address):
                    response = self.guest_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)
            else:
                with self.subTest(address=address):
                    response = self.guest_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_author_access(self):
        """Проверка доступа к 'авторским' страницам"""
        for address, access in self.dict_access.items():
            if access == 'author':
                with self.subTest(address=address):
                    response = self.authorized_author.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)
                    response = self.authorized_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_authorized_access(self):
        """Страницы, доступные только авторизованным пользователям"""
        for address, access in self.dict_access.items():
            if access == 'authorized':
                with self.subTest(address=address):
                    response = self.authorized_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_correct_templates(self):
        """URL-адрес использует соответствующий шаблон"""
        for url_name, template in self.dict_addresses_templates.items():
            with self.subTest(f'Идёт проверка URL: "{url_name}"'):
                # здесь именно автор, а не тестер, чтобы был доступ к edit
                response = self.authorized_author.get(url_name)
                error_info = (
                    f'Для "{url_name}"'
                    f'не найдён соответствующий шаблон "{template}"')
                self.assertTemplateUsed(response, template, error_info)

    def test_custom_error_templates(self):
        """Проверка вывода кастомной страницы ошибки 404."""
        response = self.authorized_author.get('/fake_page/')
        self.assertTemplateUsed(response,
                                'core/404.html',
                                'Неверный шаблон при ошибке 404')
