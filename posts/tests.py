rom
django.core.files.uploadedfile
import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Group, Post, User


class SimpleTest(TestCase):
    def setUp(self):
        self.unlogged = Client()
        self.logged = Client()
        self.user = User.objects.create_user(
            username="sarah",
            email="connor.s@skynet.com",
            password="12345")
        self.logged.force_login(self.user)
        self.group = Group.objects.create(title='New_test_group',
                                          slug='new_test_group')

    def generate_urls(self, lastpost):
        index = reverse('index')
        profile = reverse('profile', args=[self.user.username])
        post = reverse('post', args=[self.user.username, lastpost.pk])
        group = reverse('group', args=[self.group.slug])
        return [index, profile, post, group]

    def test_profile(self):
        response = self.logged.get(reverse('profile',
                                           args=[self.user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['author'].username,
                         self.user.username)

    def test_post_create_logged(self):
        response = self.logged.get(reverse('new_post'))
        self.assertEqual(response.status_code, 200)
        content = {
            'group': self.group.id,
            'author': self.user,
            'text': 'test_text'
        }
        self.logged.post(reverse('new_post'), content, follow=True)
        lastpost = Post.objects.latest('pub_date')
        self.assertTrue(
            Post.objects.all().exists()
        )

    def test_post_create_unlogged(self):
        content = {'group': self.group.id, 'text': 'test_text'}
        response = self.unlogged.post(reverse('new_post'),
                                      content, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Post.objects.all().exists()
        )

    def test_new_post_everywhere(self):
        post = Post.objects.create(text='New_test_post',
                                   author=self.user,
                                   group=self.group)
        urls = self.generate_urls(post)
        for url in urls:
            response = self.logged.get(url)
            self.assertContains(response, 'New_test_post')
            self.assertEqual(response.status_code, 200)

    def test_edit(self):
        post = Post.objects.create(text='New_test_post',
                                   author=self.user,
                                   group=self.group)
        content = {'group': self.group.id, 'author': self.user, 'text': 'edit'}
        self.logged.post(reverse('post_edit', args=[self.user.username,
                                                    post.id]), content, follow=True)
        urls = self.generate_urls(post)
        for url in urls:
            response = self.logged.get(url)
            self.assertContains(response, 'edit')
            self.assertEqual(response.status_code, 200)

    def test_404(self):
        response = self.unlogged.get('something/really/weird/')
        self.assertEqual(response.status_code, 404)

    def test_image(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile(
            'small.gif',
            small_gif,
            content_type='image/gif'
        )
        content = {
            'author': self.logged,
            'text': 'post with image',
            'group': self.group.id,
            'image': img,
        }
        response = self.logged.post(reverse('new_post'), content, follow=True)
        self.assertContains(response, '<img'.encode())
        lastpost = Post.objects.latest('pub_date')
        urls = self.generate_urls(lastpost)
        for url in urls:
            response = self.logged.get(url)
            self.assertContains(response, '<img'.encode())
            self.assertEqual(response.status_code, 200)

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
        response = self.logged.post(url)
        self.assertFormError(
            response,
            form="form",
            field="image",
            errors="Неверный формат файла")

    def test_img__tag_in_content(self):
        # Loggined user
        url = reverse('new_post')
        with open('media/posts/file.jpg', 'wb+') as img:
            response = self.loggined_client.post(url,
                                                 data={'text': self.text, 'group': self.group.id, 'image': img})
            url = reverse('a_post', kwargs={'username': self.loggined_user.username, 'post_id': 1})
            response = self.loggined_client.get(url)
            templates_list = [template.source for template in response.templates if 'img' in template.source]
            self.assertTrue(len(templates_list) > 0)
