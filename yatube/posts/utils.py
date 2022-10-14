from django.core.paginator import Paginator

from .consts import POSTS_COUNT


def paginator(request, posts):
    paginator = Paginator(posts, POSTS_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
