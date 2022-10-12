from .forms import CommentForm, PostForm
from .models import Follow, Group, Post
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from .utils import paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import cache_page


TITLE_LENGTH = 30
User = get_user_model()


@cache_page(20, key_prefix='index_page')
def index(request):
    posts = Post.objects.all()
    context = dict(posts=posts, page_obj=paginator(request, posts))
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts_by_group.all()
    # posts здесь не обязателен, и так работает, но в тестах
    # проверяться должен список постов, так что возвращаю его
    context = dict(group=group, posts=posts,
                   page_obj=paginator(request, posts))
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    posts = get_object_or_404(User, username=username).posts_by_author.all()
    posts_author = get_object_or_404(User, username=username)
    following = False
    if request.user.is_authenticated:
        author = get_object_or_404(User, username=username)
        follow = Follow.objects.filter(
            user=request.user,
            author=author)
        if follow.exists():
            following = True
    context = dict(posts=posts,
                   page_obj=paginator(request, posts),
                   following=following,
                   posts_author=posts_author)
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    imposter = False
    post = get_object_or_404(Post, id=post_id)
    short_post = str(post.text)[:TITLE_LENGTH]
    if len(short_post) == TITLE_LENGTH:
        short_post += '...'
    posts = post.author.posts_by_author.all()
    if post.author != request.user:
        imposter = True
    # sprint 6
    form = CommentForm()
    comments = get_object_or_404(Post, id=post_id).comments.all()
    # -----
    context = dict(post=post, posts=posts,
                   short_post=short_post,
                   imposter=imposter,
                   # sprint 6
                   form=form,
                   comments=comments
                   )
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST or None,
                        files=request.FILES or None)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()
            messages.success(request, 'Пост добавлен.')
            return redirect('posts:profile', request.user)
        context = dict(form=form)
        return render(request, 'posts/create_post.html', context)
    form = PostForm()
    context = dict(form=form)
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    if request.method == 'POST':
        form = PostForm(request.POST or None,
                        instance=post,
                        files=request.FILES or None)
        if form.is_valid():
            edited_post = form.save(commit=False)
            edited_post.author = request.user
            edited_post.save()
            messages.success(request, 'Пост изменён.')
            return redirect('posts:post_detail', post_id)
        return render(request, 'posts/create_post.html',
                      {'is_edit': True, 'form': form})
    form = PostForm(instance=post)
    return render(request, 'posts/create_post.html',
                  {'is_edit': True, 'form': form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """View-функция страницы, куда будут выведены посты авторов,
    на которых подписан текущий пользователь"""
    posts = Post.objects.filter(author__following__user=request.user)
    count = Follow.objects.count()
    context = dict(posts=posts,
                   count=count,
                   page_obj=paginator(request, posts))
    return render(request, 'posts/follow.html', context)

@login_required
def profile_follow(request, username):
    # Подписаться на автора
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(
        user=request.user,
        author=author)
    # Если такой подписки нет, то создать её (на себя нельзя подписаться)
    if request.user != author and not follow.exists():
        Follow.objects.create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username=username)

@login_required
def profile_unfollow(request, username):
    # Отписаться от автора
    Follow.objects.filter(
        user=request.user,
        author=get_object_or_404(User, username=username)
    ).delete()
    return redirect('posts:profile', username=username)


