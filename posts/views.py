from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def index(request):
    limit = 10
    posts = Post.objects.all()
    paginator = Paginator(posts, limit)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request, "index.html", {"page": page, "paginator": paginator}
    )


def group_posts(
    request, slug,
):
    limit = 10
    group = get_object_or_404(Group, slug=slug)
    posts = group.group_posts.all()
    paginator = Paginator(posts, limit)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request,
        "group.html",
        {"group": group, "page": page, "paginator": paginator},
    )


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("index")
    return render(request, "post_new.html", {"form": form})


def profile(request, username):
    post_limit = 10
    author = get_object_or_404(User, username=username)
    posts = author.author_posts.all()
    post_count = author.author_posts.count()
    follower_count = author.following.count()
    following_count = author.follower.count()
    paginator = Paginator(posts, post_limit)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    render_dict = {
        "author": author,
        "post_count": post_count,
        "follower_count": following_count,
        "following_count": follower_count,
        "page": page,
        "paginator": paginator,
    }
    if not request.user.is_anonymous:
        following = Follow.objects.filter(
            user=request.user, author=author
        ).exists()
        render_dict["following"] = following

    return render(request, "profile.html", render_dict)


def post_view(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author=author, pk=post_id)
    post_count = author.author_posts.count()
    follower_count = author.following.count()
    following_count = author.follower.count()
    comments = post.comments.all()
    form = CommentForm()
    return render(
        request,
        "post.html",
        {
            "post": post,
            "author": author,
            "post_count": post_count,
            "follower_count": following_count,
            "following_count": follower_count,
            "form": form,
            "comments": comments,
        },
    )


@login_required
def post_edit(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id, author=author)
    if request.user != author:
        return redirect(
            "post_view", username=request.user.username, post_id=post_id
        )
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(
                "post_view", username=request.user.username, post_id=post_id
            )
    return render(request, "post_new.html", {"form": form, "post": post},)


def page_not_found(request, exception):
    return render(request, "misc/404.html", {"path": request.path}, status=404)


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id)
    post_count = author.author_posts.count()
    follower_count = author.following.count()
    following_count = author.follower.count()
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.author = request.user
            new_comment.post = post
            new_comment.save()
            return redirect("post_view", username=username, post_id=post_id)

    return render(
        request,
        "post.html",
        {
            "post": post,
            "author": author,
            "form": form,
            "post_count": post_count,
            "follower_count": following_count,
            "following_count": follower_count,
            "comments": comments,
        },
    )


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request, "follow.html", {"page": page, "paginator": paginator,},
    )


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if user != author:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect("profile", username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=user, author=author).delete()
    return redirect("profile", username=username)
