from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Count, Prefetch


class PostQuerySet(models.QuerySet):

    def year(self, year):
        posts_at_year = self.filter(published_at__year=year).order_by('published_at')
        return posts_at_year

    def get_post_info(self):
        post = (
            self.select_related('author')
            .prefetch_related(
                Prefetch('tags', queryset=Tag.objects.annotate(
                    posts_count=Count('posts')
                ))
            )
        )
        return post

    def popular(self):
        posts_with_likes = (
            self.get_post_info()
            .annotate(likes_count=Count('likes', distinct=True))
            .order_by('-likes_count')
        )

        post_ids = [post.id for post in posts_with_likes]

        comments_data = (
            Post.objects.filter(id__in=post_ids)
            .annotate(comments_count=Count('comments', distinct=True))
            .values_list('id', 'comments_count')
        )
        comments_dict = dict(comments_data)

        for post in posts_with_likes:
            post.comments_count = comments_dict.get(post.id, 0)

        return posts_with_likes

    def fetch_with_comments_count(self):
        """
        Добавляет количество комментов к посту

        Преимущества:
        1. Чистый код
        2. Реюзабельность
        3. Помогает уменьшить нагрузку на бд
        """
        posts_with_comments = self.get_post_info()

        comments_data = (
            Post.objects.filter(id__in=[
                post.id for post in posts_with_comments
            ])
            .annotate(comments_count=Count('comments', distinct=True))
            .values_list('id', 'comments_count')
        )
        comments_dict = dict(comments_data)

        for post in posts_with_comments:
            post.comments_count = comments_dict.get(post.id, 0)

        return posts_with_comments

    def prefetch_tags_with_posts_count(self):
        return self.prefetch_related(
            Prefetch('tags', queryset=Tag.objects.with_posts_count())
        )


class TagQuerySet(models.QuerySet):
    def popular(self):
        popular_tags = (
            self.annotate(posts_count=Count('posts'))
            .order_by('-posts_count')
        )
        return popular_tags

    def with_posts_count(self):
        return self.annotate(posts_count=Count('posts'))


class Post(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Текст')
    slug = models.SlugField('Название в виде url', max_length=200)
    image = models.ImageField('Картинка')
    published_at = models.DateTimeField('Дата и время публикации')
    objects = PostQuerySet.as_manager()

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        limit_choices_to={'is_staff': True})
    likes = models.ManyToManyField(
        User,
        related_name='liked_posts',
        verbose_name='Кто лайкнул',
        blank=True)
    tags = models.ManyToManyField(
        'Tag',
        related_name='posts',
        verbose_name='Теги')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', args={'slug': self.slug})

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'пост'
        verbose_name_plural = 'посты'


class Tag(models.Model):
    title = models.CharField('Тег', max_length=20, unique=True)
    objects = TagQuerySet.as_manager()

    def __str__(self):
        return self.title

    def clean(self):
        self.title = self.title.lower()

    def get_absolute_url(self):
        return reverse('tag_filter', args={'tag_title': self.slug})

    class Meta:
        ordering = ['title']
        verbose_name = 'тег'
        verbose_name_plural = 'теги'


class Comment(models.Model):
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост, к которому написан')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор')

    text = models.TextField('Текст комментария')
    published_at = models.DateTimeField('Дата и время публикации')

    def __str__(self):
        return f'{self.author.username} under {self.post.title}'

    class Meta:
        ordering = ['published_at']
        verbose_name = 'комментарий'
        verbose_name_plural = 'комментарии'
