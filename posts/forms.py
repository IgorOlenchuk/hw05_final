from django import forms
from django.forms import ModelForm

from .models import Post, Comment


class PostForm(ModelForm):

    class Meta:

        model = Post
        group = forms.CharField(help_text='Измените группу', required=False)
        text = forms.CharField(label = 'Текст записи', help_text='Отредактируйте текст записи и нажмите "Сохранить"', widget=forms.Textarea)
        image = forms.ImageField
        fields = ["group", "text", "image"]


class CommentForm(ModelForm):

    class Meta:

        model = Comment
        text = forms.CharField(label='Текст комментария', help_text='Напишите комментарий и нажмите "Сохранить"',
                               widget=forms.Textarea)
        fields = ["text"]
