from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import Post, Comment


class PostForm(ModelForm):

    class Meta:

        model = Post
        fields = ["group", "text", "image"]
        labels = {
            'group': _('Группа'),
            'text': _('Текст'),
            'image': _('Картинка'),
        }

class CommentForm(ModelForm):

    class Meta:

        model = Comment
        fields = ["text"]
