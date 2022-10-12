from django.core.paginator import Paginator

POSTS_COUNT = 10


def paginator(request, posts):
    paginator = Paginator(posts, POSTS_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
