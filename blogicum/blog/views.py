from django.shortcuts import get_object_or_404, render, redirect
from .models import Category, Post, Location, Comment
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib import messages
from django.contrib.auth.forms import UserChangeForm
from django import forms
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Count
from .forms import PostForm, CommentForm

@login_required
def accounts_profile_fix(request):
    return redirect('blog:index')

def get_page_obj(request, queryset, per_page=10):
    """Функция для создания page_obj"""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return page_obj

def user_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    user_posts = profile_user.post_set.all()
    if request.user != profile_user:
        user_posts = user_posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )

    user_posts = user_posts.annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')

    paginator = Paginator(user_posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': profile_user,
        'page_obj': page_obj,
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    """Редактирование профиля с встроенной формой"""
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile', username=request.user.username)
    else:
        form = UserChangeForm(instance=request.user)

    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user

            # Определяем статус публикации
            if post.pub_date > timezone.now():
                # Отложенная публикация
                post.is_published = False
                messages.success(
                    request,
                    'Пост создан и будет опубликован '
                    + post.pub_date.strftime('%d.%m.%Y в %H:%M')
                )
            else:
                # Немедленная публикация
                post.is_published = True
                messages.success(request, 'Пост успешно опубликован!')

            post.save()

            # Перенаправляем на страницу профиля пользователя
            return redirect('profile', username=request.user.username)
    else:
        form = PostForm()

    context = {
        'form': form,
        'categories': Category.objects.filter(is_published=True),
        'locations': Location.objects.filter(is_published=True),
    }

    return render(request, 'blog/create.html', context)


def index(request):
    current_time = datetime.now()
    post_list = Post.objects.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=current_time
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'post_list': post_list
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, pk):

    post_queryset = Post.objects.filter(pk=pk)

    # Если пользователь не автор, добавляем фильтры
    if not (request.user.is_authenticated
            and post_queryset.filter(author=request.user).exists()):
        post_queryset = post_queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )

    # Получаем пост или 404
    post = get_object_or_404(post_queryset)

    # Остальной код...
    comments = post.comments.order_by('created_at')
    form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'form': form,
        'is_author': request.user == post.author,
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    post_list = category.post_set.filter(
        is_published=True,
        pub_date__lte=timezone.now()
    ).select_related('author', 'location').annotate(
        comment_count=Count('comments')  # Добавляем аннотацию
    ).order_by('-pub_date')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)


@login_required
def edit_post(request, pk):
    """
    Редактирование поста авторизованным пользователем.
    Только автор поста может редактировать.
    """
    post = get_object_or_404(Post, pk=pk)

    if request.user != post.author:
        messages.error(request, 'Вы можете редактировать только свои посты.')
        return redirect('blog:post_detail', pk=post.pk)

    if request.method == 'POST':
        form = PostForm(
            request.POST,
            request.FILES or None,
            instance=post
        )

        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            if post.is_published and not post.pub_date:
                post.pub_date = timezone.now()

            if post.pub_date and post.pub_date > timezone.now():
                post.is_published = False
            post.save()

            messages.success(request, 'Пост успешно обновлен!')
            return redirect('blog:post_detail', pk=post.pk)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = PostForm(instance=post)

    context = {
        'form': form,
        'post': post,
        'title': f'Редактирование: {post.title}'
    }
    return render(request, 'blog/create.html', context)


@login_required
def delete_post(request, pk):
    """Удаление поста"""
    post = get_object_or_404(Post, pk=pk)

    # Проверяем, что пользователь - автор поста
    if request.user != post.author:
        messages.error(request, 'Вы можете удалять только свои посты.')
        return redirect('blog:post_detail', pk=post.pk)

    if request.method == 'POST':
        print("POST запрос получен!")  # для отладки
        post.delete()
        print("Пост удален!")  # для отладки
        messages.success(request, 'Пост успешно удален!')
        return redirect('blog:index')
    else:
        print("GET запрос")  # для отладки

    # Используем PostForm с instance поста

    # Создаем форму с экземпляром поста
    form = PostForm(instance=post)

    context = {
        'form': form,
    }
    return render(request, 'blog/create.html', context)


@login_required
@require_POST
def add_comment(request, pk):
    """Добавление комментария (только POST)"""
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        messages.success(request, 'Комментарий успешно добавлен!')
    else:
        messages.error(request, 'Ошибка при добавлении комментария.')

    return redirect('blog:post_detail', pk=post.pk)


@login_required
def edit_comment(request, post_id, comment_id):
    """Редактирование комментария"""
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id
    )

    # Проверяем, что пользователь - автор комментария
    if request.user != comment.author:
        messages.error(request,
                       'Вы можете редактировать только свои комментарии.'
                       )
        return redirect('blog:post_detail', pk=post_id)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Комментарий успешно отредактирован!')
            return redirect('blog:post_detail', pk=post_id)
    else:
        form = CommentForm(instance=comment)

    context = {
        'form': form,
        'comment': comment,
        'post': comment.post
    }
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    """Удаление комментария"""
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post_id=post_id,
        author=request.user  # только автор может удалить
    )

    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Комментарий успешно удален!')
        return redirect('blog:post_detail', pk=post_id)

    context = {
        'comment': comment,
        'post': comment.post
    }
    return render(request, 'blog/comment.html', context)


def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)


def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403)


def handler500(request):
    return render(request, 'pages/500.html', status=500)
