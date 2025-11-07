from django import forms
from .models import Article

class ArticleCreationForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        widgets = {
            'article_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введіть назву статті'
            }),
            'article_short_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введіть коротку назву статті'
            }),
            'article_author': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введіть ім\'я автора'
            }),
            'article_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введіть короткий опис статті'
            }),
            'article_img': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'article_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'Введіть текст статті. Використовуйте переноси рядків для розділення абзаців.'
            }),
        }