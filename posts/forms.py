from django.forms import ModelForm

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ("group", "text", "image")
        labels = {"group": "Группа", "text": "Текст", "image": "Изображение"}
        help_texts = {
            "group": "Выберите группу из списка",
            "text": "* не более 100500 символов",
            "image": "В формате jpg, jpeg, png",
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ("text",)
