from django.shortcuts import get_object_or_404, render, redirect
from .models import Category, Post, Location
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.forms import UserChangeForm
from django import forms
from django.utils import timezone


def user_profile(request, username):
    # Получаем пользователя (в шаблоне он называется profile)
    profile = get_object_or_404(User, username=username)
    
    # Получаем все публикации пользователя
    posts_list = Post.objects.filter(author=profile).order_by('-pub_date')
    
    # Настраиваем пагинацию (6 постов на страницу)
    paginator = Paginator(posts_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile': profile, 
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
    """Создание новой публикации"""
    class PostForm(forms.ModelForm):
        
        class Meta:
            model = Post
            fields = ['title', 'text', 'pub_date', 'category', 'location', 'image']
        
            widgets = {
                'title': forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Введите заголовок'
                }),
                'text': forms.Textarea(attrs={
                    'class': 'form-control',
                    'rows': 10,
                    'placeholder': 'Введите текст публикации'
                }),
                'pub_date': forms.DateTimeInput(attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                }),
                'category': forms.Select(attrs={'class': 'form-select'}),
                'location': forms.Select(attrs={'class': 'form-select'}),
                'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            }
        
            labels = {
                'title': 'Заголовок',
                'text': 'Текст',
                'pub_date': 'Дата и время публикации',
                'category': 'Категория',
                'location': 'Местоположение',
                'image': 'Изображение',
        }
    
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        # Показываем только опубликованные категории и местоположения
            self.fields['category'].queryset = Category.objects.filter(is_published=True)
            self.fields['location'].queryset = Location.objects.filter(is_published=True)

        
        # Устанавливаем текущее время по умолчанию
            if not self.instance.pk:  # Только для создания нового поста
                self.fields['pub_date'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
    
        def clean_pub_date(self):
            pub_date = self.cleaned_data.get('pub_date')
            if pub_date and pub_date < timezone.now():
            # Если дата в прошлом, сразу публикуем
                self.instance.is_published = True
            return pub_date
    
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
                    'Пост создан и будет опубликован ' + 
                    post.pub_date.strftime('%d.%m.%Y в %H:%M')
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
    ).order_by('-pub_date')[:5]
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'post_list': post_list
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, pk):
    current_time = datetime.now()
    post = get_object_or_404(
        Post,
        pk=pk,
        is_published=True,
        pub_date__lte=current_time,
        category__is_published=True
    )
    context = {
        'post': post
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    current_time = datetime.now()
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post_list = Post.objects.select_related('author', 'location').filter(
        category=category,
        is_published=True,
        pub_date__lte=current_time
    ).order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'category': category,
        'post_list': post_list
    }
    return render(request, 'blog/category.html', context)

def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)

def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403)

def handler500(request):
    return render(request, 'pages/500.html', status=500)
