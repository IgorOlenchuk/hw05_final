from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Post, Group, Comment, Follow

User = get_user_model()


class ProfileTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.not_authorized_client = Client()
        self.user = User.objects.create_user(
            username="anon")
        self.client.force_login(self.user)
        self.group = Group.objects.create(title="test", slug="tt",
                                          description="test")
        self.post = Post.objects.create(text="This is my pre post!",
                                        author=self.user, group=self.group)
        self.second_author = User.objects.create_user(
            username="anonymous_poet")
        self.post_of_2d_auth = Post.objects.create(text="Second poet here!!",
                                                   author=self.second_author,
                                                   group=self.group)
        self.post_2d_author_list = list(
            Post.objects.filter(
                author=self.second_author).all())
        cache.clear()

    def check_post_on_page(self, client, user, post):
        cache.clear()
        page_list = ["index", "profile", "post", "group"]
        kwargs_list = [{}, {"username": user}, {"username": user,
                                                "post_id": post.pk},
                       {"slug": post.group.slug}]
        for pg, kw in zip(page_list, kwargs_list):
            response = client.get(reverse(pg, kwargs=kw))
            self.assertEqual(response.status_code, 200,
                             msg="Страница недоступна")
            if str(pg) != "post":
                page_object = response.context["page"].object_list
            else:
                page_object = response.context["page"]
            self.assertTrue(post in page_object,
                            msg="Пост отсутствует на странице")

    def check_img_on_post(self, client, user, post):
        page_list = ["index", "profile", "post", "group"]
        kwargs_list = [{}, {"username": user}, {"username": user,
                                                "post_id": post.pk},
                       {"slug": post.group.slug}]
        for pg, kw in zip(page_list, kwargs_list):
            response = client.get(reverse(pg, kwargs=kw))
            self.assertEqual(response.status_code, 200,
                             msg="Страница недоступна")
            self.assertIn('<img'.encode(), response.content,
                          msg="Картинка отсутствует в посте")

    def test_user_page_created(self):
        response = self.client.get(reverse("profile",
                                           kwargs={"username": self.user}))
        self.assertEqual(response.status_code, 200,
                         msg="Страницы пользователя не существует")

    def test_auth_user_can_publishing_post(self):
        url = reverse("new_post")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200,
                         msg="Страница новой записи недоступна")
        test_context = {
            "group": self.group.id,  # Optional
            "text": "This is my first post!",  # Required
        }
        response = self.client.post(url, test_context, follow=True)
        self.assertEqual(response.status_code, 200,
                         msg="Пост не создан")
        self.check_post_on_page(self.client, self.user,
                                post=Post.objects.last())

    def test_author_can_edit_post(self):
        self.post = Post.objects.create(
            text="This is my first post!", author=self.user,
            group=self.group)
        url = reverse("post_edit", kwargs={"username": self.user.username,
                                           "post_id": self.post.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200,
                         msg="Страница редактирования записи недоступна")
        test_context = {
            "group": self.group.id,  # Optional
            "text": "This is my refactored post!",  # Required
        }
        response = self.client.post(url, test_context, follow=True)
        self.assertEqual(response.status_code, 200, msg="Пост не создан")
        self.assertContains(response,
                            test_context["text"], count=1, status_code=200,
                            msg_prefix='Пост встречается больше одного раза')
        self.check_post_on_page(self.client, self.user,
                                post=Post.objects.last())

    def test_not_auth_user_cant_publishing_post(self):
        url = reverse("new_post")
        url2 = f"{reverse('login')}?next={reverse('new_post')}"
        response = self.not_authorized_client.get(url)
        self.assertEqual(response.status_code, 302,
                         msg="Страница новой записи доступна "
                             "неавторизованному пользователю или "
                             "переадрессация не произошла")
        self.assertRedirects(response, url2, status_code=302,
                             msg_prefix="Неверный редирект")

    def test_post_contains_image(self):
        url = reverse("new_post")
        expected_url = reverse("index")
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            'small.gif',
            small_gif,
            content_type='image/gif'
        )
        test_context = {
            "group": self.group.id,  # Optional
            "text": "This is my first post!",
            "image": uploaded
        }
        response = self.client.post(url, test_context, follow=True)
        self.assertEqual(response.status_code, 200,
                         msg="Пост не создан")
        self.assertRedirects(response, expected_url,
                             status_code=302,
                             target_status_code=200,
                             msg_prefix="Нет "
                                        "перенаправления на главную "
                                        "страницу",
                             fetch_redirect_response=True)
        self.check_img_on_post(self.client, self.user,
                               post=Post.objects.first())

    def test_cache_on_main_page(self):
        self.assertEqual(Post.objects.count(), 2, msg="Неверное начальное "
                                                      "количество постов")
        response = self.client.get(reverse("index"))
        page_object = response.context["page"].object_list
        self.post = Post.objects.create(text="This is my new post!",
                                        author=self.user, group=self.group)
        self.assertTrue(self.post not in page_object,
                        msg="Кэширование не работает."
                            "Пост появился на странице")
        self.assertEqual(Post.objects.count(), 3, msg="Новый пост не создан")
        cache.clear()
        response = self.client.get(reverse("index"))
        page_object = response.context["page"].object_list

        self.assertTrue(self.post in page_object,
                        msg="Пост отсутствует на странице")

    def test_auth_follow_unfollow(self):
        test_user = User.objects.create_user(username="Igor")
        self.client.get(
            reverse("profile_follow", args=[test_user.username])
        )
        self.assertEqual(Follow.objects.count(), 1)
        testpost = Post.objects.create(
            text="test text", author=test_user
        )
        response = self.client.get(reverse("follow_index"))
        self.assertEqual(response.context.get("paginator").count, 1)

    def test_auth_unfollow(self):
        test_user = User.objects.create_user(username="Igor")
        testpost = Post.objects.create(
            text="test text", author=test_user
        )
        self.client.get(
            reverse("profile_follow", args=[test_user.username])
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.client.get(
            reverse("profile_unfollow", args=[test_user.username])
        )
        self.assertEqual(Follow.objects.count(), 0)
        response = self.client.get(reverse("follow_index"))
        self.assertEqual(response.context.get("paginator").count, 0)

    def test_not_auth_user_cant_follow(self):
        self.client.post(
            reverse("profile_follow", args=[self.client])
        )
        self.assertEqual(Follow.objects.count(), 0)
        response = self.client.get(reverse("follow_index"))
        self.assertEqual(
            response.context.get("paginator").count, 0)

    def test_auth_user_can_comment_post(self):
        testpost = Post.objects.create(text="test text", author=self.user)
        url = reverse("add_comment", args=[self.user.username, testpost.id])
        test_context = {
            "text": "This is my comment",
            "author": self.user,
            "post": testpost.id,
        }
        response = self.client.post(
            url,
            test_context,
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(response.status_code, 200,
                         msg="комментарий не создан")

    def test_not_auth_user_cant_comment_post(self):
        testpost = Post.objects.create(text="test text", author=self.user)
        self.assertEqual(Comment.objects.count(), 0)
        response = self.not_authorized_client.post(
            reverse("add_comment",
                    args=[self.user.username, testpost.id])
        )
        self.assertEqual(response.status_code, 302,
                         msg="Страница комментирования доступна "
                             "неавторизованному пользователю")

    def test_followed_auth_posts_on_page(self):
        self.client.get(reverse("profile_follow",
                                kwargs={"username":
                                            self.second_author}))
        redirect_url = reverse("follow_index")
        response = self.client.get(redirect_url)
        page_object = response.context["page"].object_list
        self.assertEqual(page_object, self.post_2d_author_list,
                         msg="На странице подписок только посты автора, на "
                             "которого подписались")

    def test_unfollowed_auth_posts_not_on_page(self):
        redirect_url = reverse("follow_index")
        response = self.client.get(redirect_url)
        page_object = response.context["page"].object_list
        self.assertNotIn(page_object, self.post_2d_author_list,
                         msg="На странице подписок присутствуют посты "
                             "авторов, подписка на которых не оформлена")

    def test_404(self):
        response = self.client.get('something/really/weird/')
        self.assertEqual(response.status_code, 404)

    def test_wrong_file(self):
        wrong_file = (
            b"\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
            b"\x02\x4c\x01\x00\x3b"
        )
        wrong = SimpleUploadedFile(
            "wrong_file.doc",
            wrong_file,
            content_type="doc"
        )
        url = reverse("new_post")
        data = {
            "text": "Wrong image",
            "group": self.group.id,
            "image": wrong
        }
        response = self.client.post(url, data=data)
        self.assertFormError(
            response,
            form="form",
            field="image",
            errors='Загрузите правильное изображение.'
                   ' Файл, который вы загрузили,'
                   ' поврежден или не является изображением.'
        )
