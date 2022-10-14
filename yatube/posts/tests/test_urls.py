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
        cls.list_addresses = [
            '/unexisting_page/',
            '/',
            '/group/IamGroupSlug/',
            '/profile/IamTester/',
            f'/posts/{cls.post.pk}/',
            f'/posts/{cls.post.pk}/edit/',
            '/create/'
        ]
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

    def test_access_create(self):
        """Проверка доступа к созданию поста"""
        response = self.authorized_client.get(self.list_addresses[6])
        error_info = 'Авторизированный пользователь не может создавать посты'
        self.assertEqual(response.status_code, HTTPStatus.OK, error_info)

    def test_general_access(self):
        """Проверка доступа к общедоступным страницам"""
        for address in self.list_addresses[:5]:
            if address == '/unexisting_page/':
                response = self.guest_client.get(address)
                error_info = 'Обнаружилась несуществующая страница'
                self.assertEqual(response.status_code,
                                 HTTPStatus.NOT_FOUND, error_info)
            else:
                response = self.guest_client.get(address)
                error_info = (f'Любой пользователь '
                              f'не получил доступ к {address}')
                self.assertEqual(response.status_code,
                                 HTTPStatus.OK, error_info)

    def test_post_edit_not_authorized(self):
        """Проверка доступа неавторизованного
         пользователя к редактированию поста"""
        response = self.guest_client.get(self.list_addresses[5])
        error_info = ('Не сработал redirect '
                      'для неавторизированного пользователя')
        self.assertEqual(response.status_code, HTTPStatus.FOUND, error_info)

    def test_post_edit_authorized_not_author(self):
        """Проверка доступа авторизированного
         не автора к редактированию поста"""
        response = self.authorized_client.get(self.list_addresses[5])
        error_info = 'Не сработал redirect для не автора поста'
        self.assertEqual(response.status_code, HTTPStatus.FOUND, error_info)

    def test_post_edit_authorized_author(self):
        """Проверка доступа автора к редактированию поста"""
        # здесь нужен именно автор!
        response = self.authorized_author.get(self.list_addresses[5])
        error_info = ('Автор не получил доступ'
                      ' к редактированию своего поста')
        self.assertEqual(response.status_code, HTTPStatus.OK, error_info)

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
        response = self.authorized_author.get(self.list_addresses[0])
        self.assertTemplateUsed(response,
                                'core/404.html',
                                'Неверный шаблон при ошибке 404')
