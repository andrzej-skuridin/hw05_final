from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.db import models
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from datetime import datetime as dt
import tempfile
import shutil
from PIL import Image, ImageChops
from http import HTTPStatus

from ..models import Comment, Group, Follow, Post, User
from ..forms import PostForm
from ..utils import POSTS_COUNT

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём автора
        cls.my_author1 = User.objects.create_user(username='IamAuthor')
        # Автор для теста подписки
        cls.my_author2 = User.objects.create_user(username='AnotherAuthor')
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

        # Создаём группы
        cls.group = Group.objects.create(
            title='IamGroup',
            slug='IamGroupSlug')
        cls.another_group = Group.objects.create(
            title='IamAnotherGroup',
            slug='IamAnotherGroupSlug')
        # Создаём пост
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.my_author1,
            pub_date=dt.now(),
            group=cls.group,
            image=cls.picture)
        cls.list_addresses = [
            '/',
            f'/group/{cls.group.slug}/',
            f'/profile/{cls.post.author}/',
            f'/posts/{cls.post.pk}/']

    def setUp(self):
        # Создаем авторизированный клиент-тестер
        self.authorized_client = Client()
        # сразу делаем тестера автором (my_author1), дабы упростить тесты
        self.user = self.post.author
        self.authorized_client.force_login(self.user)
        # чистим кэш, чтобы не ломались тесты, связанные с индексом
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_detail_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        pk = PostsViewsTests.post.pk
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': pk}))
        context_types = {
            'post': Post,
            'posts': models.query.QuerySet,
            'short_post': str,
            'imposter': bool
        }
        for value, expected in context_types.items():
            with self.subTest(f'Проверяется {value}'):
                result = response.context.get(value)
                self.assertIsInstance(result, expected)

    def test_create_post_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_create'))
        context_types = {'form': PostForm}
        for value, expected in context_types.items():
            with self.subTest(f'Проверяется {value}'):
                result = response.context.get(value)
                self.assertIsInstance(result, expected)

    def test_edit_post_context(self):
        """Шаблон create_post сформирован с
        правильным контекстом при редактировании поста."""
        pk = PostsViewsTests.post.pk
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': pk}))
        context_types = {'form': PostForm}
        for value, expected in context_types.items():
            with self.subTest(f'Проверяется {value}'):
                result = response.context.get(value)
                self.assertIsInstance(result, expected)

    def test_index_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        context_types = {'posts': models.query.QuerySet}
        for value, expected in context_types.items():
            with self.subTest(f'Проверяется {value}'):
                result = response.context.get(value)
                self.assertIsInstance(result, expected)

    def test_group_list_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        group_slug = PostsViewsTests.group.slug
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': group_slug}))
        context_types = {
            'posts': models.query.QuerySet,
            'group': Group}

        for value, expected in context_types.items():
            with self.subTest(f'Проверяется {value}'):
                result = response.context.get(value)
                self.assertIsInstance(result, expected)

    def test_profile_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': self.my_author1.username}))
        context_types = {
            'posts': models.query.QuerySet,
            'posts_author': User}

        for value, expected in context_types.items():
            with self.subTest(f'Проверяется {value}'):
                result = response.context.get(value)
                self.assertIsInstance(result, expected)

    def test_post_appears(self):
        """Пост появляется на страницах"""
        context_data = {
            'posts:profile': ({'username': self.my_author1.username},
                              'posts'),
            'posts:index': 'posts'}
        for reverse_address, data in context_data.items():
            with self.subTest(f'Проверяется "{reverse_address}"'):
                if reverse_address == 'posts:index':
                    response = self.authorized_client.get(
                        reverse(reverse_address))
                else:
                    response = self.authorized_client.get(
                        reverse(reverse_address, kwargs=data[0]))

                    self.assertEqual(len(response.context[data[1]]), 1)

                Post.objects.create(
                    text='Тестовый текст поста 5',
                    author=self.my_author1,
                    pub_date=dt.now()
                )

                if reverse_address == 'posts:index':
                    response = self.authorized_client.get(
                        reverse(reverse_address))
                else:
                    response = self.authorized_client.get(
                        reverse(reverse_address, kwargs=data[0]))

                    self.assertEqual(len(response.context[data[1]]), 2)

    def test_post_appears_in_correct_group(self):
        # проверка появления в правильной группе (подсчёт, сколько было)
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertEqual(len(response.context['posts']), 1)
        # проверка появления в неправильной группе (подсчёт, сколько было)
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.another_group.slug}))
        self.assertEqual(len(response.context['posts']), 0)

        # делаем новый пост
        Post.objects.create(
            text='Тестовый текст поста 5',
            author=self.my_author1,
            group=self.group,
            pub_date=dt.now()
        )

        # проверка появления в правильной группе (подсчёт, сколько стало)
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertEqual(len(response.context['posts']), 2)
        # проверка появления в неправильной группе (подсчёт, сколько стало)
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': self.another_group.slug}))
        self.assertEqual(len(response.context['posts']), 0)

    def test_image_in_context(self):
        """Проверяет наличие картинки в контексте страницы."""
        response1 = self.authorized_client.get(self.list_addresses[3])
        actual_pic = Image.open(response1.context.get('post').image)
        expected_pic = Image.open(self.picture)
        result = ImageChops.difference(actual_pic, expected_pic).getbbox()
        self.assertEqual(None, result)
        for address in self.list_addresses[:3]:
            with self.subTest(f'Идёт проверка URL: "{address}"'):
                response2 = self.authorized_client.get(address)
                # если в сетапе добавить ещё один пост, этот тест сломается,
                # скорре всего из-за [0]. при случае надо будет поправить
                actual_pic = Image.open(
                    response2.context.get('posts')[0].image)
                expected_pic = Image.open(self.picture)
                result = ImageChops.difference(actual_pic,
                                               expected_pic).getbbox()
                self.assertEqual(None, result)

    def test_cache_index(self):
        """Проверяем, что index кэшируется."""
        check1 = self.authorized_client.get(
            reverse('posts:index')).content
        # делаем новый пост
        Post.objects.create(
            text='Тестовый текст поста 5',
            author=self.user,
            group=self.group
        )
        check2 = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertEqual(check1, check2)
        cache.clear()
        check3 = self.authorized_client.get(
            reverse('posts:index')).content
        self.assertNotEqual(check3, check1)

    def test_follow_unfollow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей и удалять их из подписок."""
        # Создаём пост для проверки подписки
        # этот пост портит тест на изображение,
        # поэтому он тут, а не в сетапе
        another_post = Post.objects.create(
            text='Тестовый текст поста',
            author=self.my_author2,
            pub_date=dt.now()
        )
        follow_count1 = Follow.objects.count()
        response1 = self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.my_author2}))
        self.assertRedirects(
            response1, reverse(
                'posts:profile',
                kwargs={'username': self.my_author2}))
        follow_count2 = Follow.objects.count()
        self.assertEqual(follow_count1 + 1, follow_count2)
        response2 = self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.my_author2}))
        self.assertRedirects(
            response2, reverse(
                'posts:profile',
                kwargs={'username': self.my_author2}))
        follow_count3 = Follow.objects.count()
        self.assertEqual(follow_count1, follow_count3)

    def test_post_in_subscribtions(self):
        """Новая запись пользователя появляется в ленте тех,
         кто на него подписан и не появляется в ленте тех, кто не подписан"""
        # 1) считаем число постов в подписках автора1 (их ноль, подписок нет)
        response0 = self.authorized_client.get(
            reverse(
                'posts:follow_index'))
        count1 = len(response0.context['posts'])
        # 2) подписываем автора 1 на автора 2
        response1 = self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.my_author2}))
        # 3) публикуем от имени автора 2 новый пост
        another_post = Post.objects.create(
            text='Тестовый текст поста',
            author=self.my_author2,
            pub_date=dt.now())
        # 4) считаем число постов в подписках автора1 (их на 1 больше)
        response2 = self.authorized_client.get(
            reverse(
                'posts:follow_index'))
        count2 = len(response2.context['posts'])
        # проверяем, что у автора1 на 1 пост больше в подписках
        self.assertEqual(count1 + 1, count2)
        # 5) считаем число постов в подписках автора2
        # их должно быть 0
        # перелогиниваемся за автора2
        self.user = self.my_author2
        self.authorized_client.force_login(self.user)
        response3 = self.authorized_client.get(
            reverse(
                'posts:follow_index'))
        count3 = len(response3.context['posts'])
        self.assertEqual(0, count3)

    def test_authorized_comments(self):
        """Комментировать посты может только авторизованный пользователь"""
        # проверяем доступ авторизированного пользователя
        comment_form = {'text': 'Текст комментария'}
        response1 = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.pk}),
            data=comment_form)
        print(response1.status_code)
        # проверяем доступ неавторизированного пользователя
        self.guest_client = Client()
        response2 = self.guest_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.pk}),
            data=comment_form)
        # авторизированного должно перенаправить на детали поста,
        # неавторизированного - на страницу авторизации
        self.assertRedirects(response1,
                             f'/posts/{self.post.pk}/')
        self.assertRedirects(response2,
                             f'/auth/login/?next='
                             f'/posts/{self.post.pk}/comment/')

    def test_comment_appears_in_post_details(self):
        """После успешной отправки комментарий появляется на странице поста"""
        # Проверяем число комментариев до отправки комментария
        response1 = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        check1 = response1.context.get('comments')
        self.assertEqual(0, len(check1))
        # отправляем комментарий
        comment_form = {'text': 'Текст комментария'}
        self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.pk}),
            data=comment_form)
        # Проверяем число комментариев после отправки комментария
        response2 = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        check2 = response2.context.get('comments')
        self.assertEqual(len(check1) + 1, len(check2),
                         'Число комментариев не совпало с ожидаемым')


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём автора
        cls.my_author = User.objects.create_user(username='IamAuthor')

        # Создаём группу
        cls.group = Group.objects.create(
            title='IamGroup',
            slug='IamGroupSlug'
        )

        # Создаём посты

        for i in range(POSTS_COUNT + 1):
            Post.objects.create(
                text='Тестовый текст поста',
                author=cls.my_author,
                pub_date=dt.now(),
                group=cls.group
            )

    def test_paginator(self):
        """Проверяет работу Paginator."""
        reverse_names = {
            'posts:index': {None: None},
            'posts:group_list': {'slug': self.group.slug},
            'posts:profile': {'username': self.my_author.username}
        }
        for reverse_name, kwarg in reverse_names.items():
            with self.subTest(f'Идёт проверка: "{reverse_name}"'):
                # проверка первой страницы
                if reverse_name != 'posts:index':
                    response = self.client.get(
                        reverse(reverse_name, kwargs=kwarg) + '?page=1')
                else:
                    response = self.client.get(
                        reverse(reverse_name) + '?page=1')
                self.assertEqual(len(response.context['page_obj']),
                                 POSTS_COUNT)
                # проверка второй страницы
                if reverse_name != 'posts:index':
                    response = self.client.get(
                        reverse(reverse_name, kwargs=kwarg) + '?page=2')
                else:
                    response = self.client.get(
                        reverse(reverse_name) + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 1)
