from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_post_model_correct_str_method(self):
        """Проверяем, что у модели Post корректно работает __str__."""
        actual_result = self.post.__str__()
        expected_result = self.post.text[:15]
        self.assertEqual(expected_result, actual_result)

    def test_group_model_correct_str_method(self):
        """Проверяем, что у модели Group корректно работает __str__."""
        actual_result = self.group.__str__()
        expected_result = self.group.title
        self.assertEqual(expected_result, actual_result)
