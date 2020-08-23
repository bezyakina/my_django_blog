from time import sleep

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User


class PostAppTest(TestCase):
    def setUp(self):
        # создание авторизованного пользователя
        self.authorized_client = Client()
        self.user = User.objects.create_user(
            username="test", email="test@test.ru", password="123456"
        )
        self.authorized_client.force_login(self.user)

        # создание неавторизованного пользователя
        self.unauthorized_client = Client()
        self.unauthorized_client.logout()

        # создание тестовой группы
        self.group = Group.objects.create(
            title="title", slug="slug", description="description"
        )

        # создание тестовых текстов для постов
        self.text_1 = "some text..."
        self.text_2 = "yet another text..."

        # тестовые данные для тестирования постов на наличие изображений
        self.tag = "<img "

        self.error_message = (
            "Загрузите правильное изображение. Файл, "
            "который вы загрузили, поврежден или не "
            "является изображением."
        )

        # создание автора и поста для подписки
        self.author_1 = User.objects.create_user(
            username="author_1", password=12345
        )
        self.post_1_author_1 = Post.objects.create(
            text=self.text_1, group=self.group, author=self.author_1,
        )

        # тестовый комментарий
        self.comment_text = "some comments..."

        # тестовый пост
        self.post_without_image = Post.objects.create(
            text=self.text_1, group=self.group, author=self.user,
        )

    def test_user_profile_page(self):
        """
        Проверка наличия персональной страницы пользователя после его
        регистрации.
        """

        response = self.authorized_client.get(
            reverse("profile", kwargs={"username": self.user.username})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual("profile.html", response.templates[0].name)
        self.assertIn("author", response.context)
        self.assertIn("paginator", response.context)

    def test_new_post_with_auth(self):
        """
        Проверка возможности опубликовать пост для авторизованного
        пользователя.
        """

        response = self.authorized_client.get("new_post")
        self.assertEqual(response.status_code, 404)
        response = self.authorized_client.post(
            reverse("new_post"),
            data={"text": self.text_1, "group": self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        post = Post.objects.all().first()
        self.assertEqual(Post.objects.count(), post.id)

    def test_new_post_without_auth(self):
        """
        Проверка невозможности опубликовать пост для неавторизованного
        пользователя и последующего редиректа пользователя на страницу входа.
        """

        response = self.unauthorized_client.post(
            reverse("new_post"),
            data={"text": self.text_1, "group": self.group.id},
            follow=True,
        )

        login_url = reverse("login")
        new_post_url = reverse("new_post")
        target_url = f"{login_url}?next={new_post_url}"

        self.assertRedirects(response, target_url)

    def post_contains_params_on_all_pages(
        self, post_id, text=None, image=None
    ):
        """
        Вспомогательная функция для проверки отображения постов и их
        содержимого на всех страницах.
        """

        urls = [
            reverse("index"),
            reverse("profile", kwargs={"username": self.user.username}),
            reverse(
                "post_view",
                kwargs={"username": self.user.username, "post_id": post_id},
            ),
            reverse("group_posts", kwargs={"slug": self.group.slug}),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                if image:
                    self.assertContains(response, image)
                else:
                    self.assertContains(response, self.group)
                    self.assertContains(response, text)

    def test_new_post_display_on_all_pages(self):
        """
        Проверка отображения опубликованного поста на главной странице сайта,
        на персональной странице пользователя, на отдельной странице поста и
        на странице группы.
        """

        self.authorized_client.post(
            reverse("new_post"),
            data={"text": self.text_1, "group": self.group.id},
            follow=True,
        )
        post = Post.objects.all().first()
        self.post_contains_params_on_all_pages(post.id, text=self.text_1)

    def test_edited_post_display_on_all_pages(self):
        """
        Проверка отображения отредактированного поста на главной странице
        сайта, на персональной странице пользователя, на отдельной странице
        поста и на странице группы.
        """

        self.authorized_client.post(
            reverse(
                "post_edit",
                kwargs={
                    "username": self.post_without_image.author,
                    "post_id": self.post_without_image.id,
                },
            ),
            data={"text": self.text_2, "group": self.group.id},
            follow=True,
        )

        self.post_contains_params_on_all_pages(
            self.post_without_image.id, text=self.text_2
        )

    def test_404(self):
        """
        Проверка возвращения кода 404 при переходе на несуществующую страницу.
        """
        response = self.unauthorized_client.get("/404/")
        self.assertEqual(response.status_code, 404)
        response = self.authorized_client.get("/404/")
        self.assertEqual(response.status_code, 404)

    def test_post_view_image_display_on_all_pages(self):
        """
        Проверка загрузки и отображения изображеения на всех страницах с
        постами.
        """

        small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04"
            b"\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
            b"\x02\x4c\x01\x00\x3b"
        )
        img = SimpleUploadedFile(
            "small.gif", small_gif, content_type="image/gif"
        )

        post_with_image = Post.objects.create(
            text=self.text_1, group=self.group, author=self.user, image=img,
        )

        cache.clear()

        self.post_contains_params_on_all_pages(
            post_with_image.id, image=self.tag
        )

    def test_non_image_file_upload_protection(self):
        """
        Проверка срабатывания защиты при загрузке неграфических файлов.
        """

        not_img = SimpleUploadedFile(
            "small.txt", b"test", content_type="text/plain"
        )

        url = reverse("new_post")
        response = self.authorized_client.post(
            url, {"text": self.text_1, "image": not_img}
        )
        self.assertFormError(response, "form", "image", self.error_message)

    def test_index_page_cache(self):
        """
        Проверка кеширования главной страницы.
        """

        cache.clear()

        Post.objects.create(
            text="cached", author=self.user,
        )
        response = self.authorized_client.get(reverse("index"))
        self.assertContains(response, "cached")

        Post.objects.create(
            text="not_cached", author=self.user,
        )
        response = self.authorized_client.get(reverse("index"))
        self.assertNotContains(response, "not_cached")

        sleep(20)

        response = self.authorized_client.get(reverse("index"))
        self.assertContains(response, "not_cached")

    def test_auth_user_follow_unfollow(self):
        """
        Авторизованный пользователь может подписываться на других пользователей
        и удалять их из подписок.
        """

        response = self.authorized_client.get(
            reverse("profile", kwargs={"username": self.author_1.username})
        )
        self.assertContains(response, "Подписчиков: 0")

        self.authorized_client.get(
            reverse(
                "profile_follow", kwargs={"username": self.author_1.username}
            )
        )
        response = self.authorized_client.get(
            reverse("profile", kwargs={"username": self.author_1.username})
        )
        self.assertContains(response, "Подписчиков: 1")

        self.authorized_client.get(
            reverse(
                "profile_unfollow", kwargs={"username": self.author_1.username}
            )
        )
        response = self.authorized_client.get(
            reverse("profile", kwargs={"username": self.author_1.username})
        )
        self.assertContains(response, "Подписчиков: 0")

    def test_follower_index(self):
        """
        Новая запись пользователя появляется в ленте тех, кто на него подписан
        и не появляется в ленте тех, кто не подписан на него.
        """

        response = self.authorized_client.get(reverse("follow_index"))
        self.assertNotContains(response, self.text_1)

        cache.clear()

        self.authorized_client.get(
            reverse(
                "profile_follow", kwargs={"username": self.author_1.username}
            )
        )
        response = self.authorized_client.get(reverse("follow_index"))
        self.assertContains(response, self.text_1)

    def test_only_auth_user_add_comment(self):
        """
        Только авторизированный пользователь может комментировать посты.
        """

        response = self.authorized_client.post(
            reverse(
                "add_comment",
                kwargs={
                    "username": self.user.username,
                    "post_id": self.post_without_image.id,
                },
            ),
            {"text": self.comment_text},
            follow=True,
        )
        self.assertContains(response, self.comment_text)

        response = self.unauthorized_client.post(
            reverse(
                "add_comment",
                kwargs={
                    "username": self.user.username,
                    "post_id": self.post_without_image.id,
                },
            ),
            {"text": self.comment_text},
            follow=True,
        )
        self.assertNotContains(response, self.comment_text)
