from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache
from .models import *

User = get_user_model()


class ProfileTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.not_authorized_client = Client()
        self.user = User.objects.create_user(
            username="maria")
        self.client.force_login(self.user)
        self.group = Group.objects.create(title="test", slug="super",
                                          description="test")
        self.file_path = 'image.jpg'
        self.post = Post.objects.create(text="New post",
                                        author=self.user, group=self.group)
        self.second_author = User.objects.create_user(
            username="igor")
        self.post_of_2d_auth = Post.objects.create(text="second author",
                                                   author=self.second_author,
                                                   group=self.group)
        self.post_2d_author_list = list(
            Post.objects.filter(
                author=self.second_author).all())
        cache.clear()

    def test_post_on_page(self, client, user, post):
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
                self.assertTrue(post in page_object,
                                msg="Пост отсутствует на странице")
            else:
                page_object = response.context["post"].text
                self.assertTrue(str(post) in page_object,
                                msg="Пост отсутствует на странице")

    def test_img_on_post(self, client, user, post):
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
        self.test_post_on_page(self.client, self.user,
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
        self.test_post_on_page(self.client, self.user,
                                post=Post.objects.last())

    def test_not_auth_user_cant_publishing_post(self):
        url = reverse('new_post')
        redirect_url = f"/auth/login/?next={reverse('new_post')}"
        response = self.not_authorized_client.get(url)
        self.assertEqual(response.status_code, 302,
                         msg="Страница новой записи доступна "
                             "неавторизованному пользователю или "
                             "переадрессация не произошла")
        self.assertRedirects(response, redirect_url, status_code=302,
                             msg_prefix="Неверный редирект")

    def test_post_contains_image(self):
        url = reverse("new_post")
        expected_url = reverse("index")
        with open(self.file_path, 'rb') as img:
            test_context = {
                "group": self.group.id,  # Optional
                "text": "This is my first post!",
                "image": img
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
            self.test_img_on_post(self.client, self.user,
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

    def test_auth_user_can_follow_and_unfollow(self):
        url = reverse("profile_follow", kwargs={"username":
                                                    self.second_author})
        redirect_url = f"/follow/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302,
                         msg="Страница подписки не доступна "
                             "авторизованному пользователю")
        self.assertRedirects(response, redirect_url, status_code=302,
                             msg_prefix="Неверный редирект")
        url = reverse("profile_unfollow",
                      kwargs={"username": self.second_author})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302,
                         msg="Функция отписки не доступна "
                             "авторизованному пользователю")

    def test_not_auth_user_cant_follow(self):
        url = reverse("profile_follow", kwargs={"username": self.user})
        redirect_url = f"/auth/login/?next=/{self.user}/follow/"
        response = self.not_authorized_client.get(url)
        self.assertEqual(response.status_code, 302,
                         msg="Страница подписки на автора доступна "
                             "неавтризованному пользователю")
        self.assertRedirects(response, redirect_url, status_code=302,
                             msg_prefix="Неверный редирект")

    def test_auth_user_can_comment_post(self):
        testpost = Post.objects.create(text="test text", author=self.user)
        url = reverse("add_comment", args=[self.user.username, testpost.id])
        response = self.client.get(
            url,
            {"text": "test comment"},
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), 1)

    def test_not_auth_user_cant_comment_post(self):
        testpost = Post.objects.create(text="test text", author=self.user)
        url = reverse("add_comment", args=[self.user.username, testpost.id])
        response = self.not_authorized_client.get(
            url,
            {"text": "test comment"},
            follow=True,
        )
        self.assertEqual(Comment.objects.count(), 0)

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
