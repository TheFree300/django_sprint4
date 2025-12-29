from django import forms 
from .models import Post, Comment, Category, Location
from django.utils import timezone

class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        exclude = ['author', 'created_at']

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
                },
                format='%d.%m.%Y %H:%M'
            ),
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
        
        # Фильтрация
        self.fields['category'].queryset = Category.objects.filter(
            is_published=True
        )
        self.fields['location'].queryset = Location.objects.filter(
            is_published=True
        )
        
        # ТОЛЬКО установка начального значения
        # Не пытаемся исправлять логику здесь
        if self.instance and self.instance.pk and self.instance.pub_date:
            self.initial['pub_date'] = self.instance.pub_date.strftime(
                '%Y-%m-%dT%H:%M'
            )
        else:
            self.initial['pub_date'] = timezone.now().strftime('%Y-%m-%dT%H:%M')

    def clean_pub_date(self):
        """Одна единственная функция для работы с pub_date"""
        pub_date = self.cleaned_data.get('pub_date')
        
        # Ваша логика: дата в прошлом = автоматическая публикация
        if pub_date and pub_date < timezone.now():
            self.instance.is_published = True
        
        return pub_date


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите ваш комментарий...'
            })
        }
        labels = {
            'text': ''
        }