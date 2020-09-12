from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Post, Group, Comment, Follow

User = get_user_model()


@cache_page(60 * 15)
def index(request):
    post_list = Post.objects.order_by('-pub_date').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context ={
        'page': page,
        'paginator': paginator,
    }
    return render(request, 'index.html', context, content_type='text/html', status=200)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.group_posts.all()
    paginator = Paginator(posts, 12)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context ={
        'page': page,
        'paginator': paginator,
        'group': group,
        'posts': posts,
    }
    return render(request, 'group.html', context)


def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('index')
    else:
        form = PostForm()
    return render(request, 'new.html', {'form': form})


def profile(request, username):
    profile = get_object_or_404(get_user_model(), username=username)
    post_list = profile.author_posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    count_post = profile.author_posts.all().count()
    form = CommentForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect("post", username=request.user.username, post_id=post_id)
    context = {
        "profile": profile,
        'page': page,
        'paginator': paginator,
        'count_post': count_post,
        'form': form,
    }
    return render(request, 'profile.html', context)


def post_view(request, username, post_id):
    profile = get_object_or_404(get_user_model(), username=username)
    post = get_object_or_404(Post, id=post_id, author__username=username)
    post_list = Post.objects.order_by('-pub_date').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    items = Comment.objects.filter(post_id=post_id).all()
    form = CommentForm(request.POST or None)
    context = {
        'profile': profile,
        'post': post,
        'page': page,
        'paginator': paginator,
        'items': items,
        'form': form,
    }
    return render(request, 'post.html', context)


@login_required
def post_edit(request, username, post_id):
    profile = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id, author=profile)
    if request.user != profile:
        return redirect('post', username=username, post_id=post_id)
    # добавим в form свойство files
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect("post", username=request.user.username, post_id=post_id)
    return render(
        request, 'new.html', {'form': form, 'post': post},
    )


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    url = reverse(
        "post",
        kwargs={"username": username, "post_id": post_id}
    )
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            form.instance.author = request.user
            form.instance.post = post
            form.save()
            return redirect(url)
    return redirect(url)


@login_required
def follow_index(request):
    follower = request.user.follower.all()
    follower_list = [item.author for item in follower]
    post_list = Post.objects.filter(author__in=follower_list)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    context = {
        'page': page,
        'paginator': paginator,
    }
    return render(request, "follow.html", context)


@login_required
def profile_follow(request, username):
    follower = request.user
    following = get_object_or_404(User, username=username)
    object_exists = Follow.objects.filter(user=follower, author=following)
    if not username == follower.username and not object_exists:
        Follow.objects.create(user=follower, author=following)
    return redirect(reverse('profile', args=(username,)))


@login_required
def profile_unfollow(request, username):
    my_user = request.user
    profile = get_object_or_404(User, username=username)
    authors = Follow.objects.filter(user=my_user, author=profile)
    if authors.exists():
        authors.delete()
    return redirect("profile", username=request.user.username)
