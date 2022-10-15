from django.test import TestCase

from ..models import Group, Post, User, META_STR_LEN
from ..consts import (NAME_USER,
                      DESCRIPTION,
                      POST_TEXT,
                      NAME_GROUP,
                      SLUG)


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=NAME_USER)
        cls.group = Group.objects.create(
            title=NAME_GROUP,
            slug=SLUG,
            description=DESCRIPTION,
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=POST_TEXT,
        )

    def test_post_model_correct_str_method(self):
        """Проверяем, что у модели Post корректно работает __str__."""
        actual_result = self.post.__str__()
        expected_result = self.post.text[:META_STR_LEN]
        self.assertEqual(expected_result, actual_result)

    def test_group_model_correct_str_method(self):
        """Проверяем, что у модели Group корректно работает __str__."""
        actual_result = self.group.__str__()
        expected_result = self.group.title
        self.assertEqual(expected_result, actual_result)
