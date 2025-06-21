from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Prefetch
from blog.models import Comment, Post, Tag


def get_popular_data(limit=5):
    popular_tags = Tag.objects.popular()[:limit]
    popular_posts = Post.objects.popular()[:limit]
    return popular_tags, popular_posts


def serialize_post(post):
    tags = post.tags.all()
    first_tag = tags.first()
    return {
        'title': post.title,
        'teaser_text': post.text[:200],
        'author': post.author.username,
        'comments_amount': post.comments_count,
        'image_url': post.image.url if post.image else None,
        'published_at': post.published_at,
        'slug': post.slug,
        'tags': [serialize_tag(tag) for tag in tags],
        'first_tag_title': first_tag.title,
    }


def serialize_tag(tag):
    return {
        'title': tag.title,
        'posts_with_tag': tag.posts_count,
    }


def index(request):

    most_popular_tags, most_popular_posts = get_popular_data()
    most_fresh_posts = (
        Post.objects.order_by('-published_at')[:5]
        .fetch_with_comments_count()
    )

    context = {
        'most_popular_posts': [
            serialize_post(post) for post in most_popular_posts
        ],
        'page_posts': [
            serialize_post(post) for post in most_fresh_posts
        ],
        'popular_tags': [
            serialize_tag(tag) for tag in most_popular_tags
        ],
    }
    return render(request, 'index.html', context)


def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.filter(slug=slug)
        .select_related('author')
        .prefetch_tags_with_posts_count()
        .prefetch_related(
            Prefetch('comments', queryset=Comment.objects.select_related(
                'author'
            )),
        )
        .annotate(
            comments_count=Count('comments', distinct=True),
            likes_count=Count('likes', distinct=True)
        )
        .first()
    )

    serialized_comments = [
        {
            'text': comment.text,
            'published_at': comment.published_at,
            'author': comment.author.username,
        }
        for comment in post.comments.all()
    ]

    serialized_post = {
        'title': post.title,
        'text': post.text,
        'author': post.author.username,
        'comments': serialized_comments,
        'likes_amount': post.likes_count,
        'image_url': post.image.url if post.image else None,
        'published_at': post.published_at,
        'slug': post.slug,
        'tags': [serialize_tag(tag) for tag in post.tags.all()],
    }

    most_popular_tags, most_popular_posts = get_popular_data()

    context = {
        'post': serialized_post,
        'popular_tags': [serialize_tag(tag) for tag in most_popular_tags],
        'most_popular_posts': [
            serialize_post(post) for post in most_popular_posts
        ],
    }
    return render(request, 'post-details.html', context)


def tag_filter(request, tag_title):
    tag = get_object_or_404(
        Tag.objects.annotate(posts_count=Count('posts')),
        title=tag_title
    )

    related_posts = (
        tag.posts
        .select_related('author')
        .prefetch_tags_with_posts_count()
        .annotate(comments_count=Count('comments'))
        [:20]
    )

    most_popular_tags, most_popular_posts = get_popular_data()

    context = {
        'tag': tag.title,
        'popular_tags': [serialize_tag(tag) for tag in most_popular_tags],
        'posts': [serialize_post(post) for post in related_posts],
        'most_popular_posts': [
            serialize_post(post) for post in most_popular_posts
        ],
    }
    return render(request, 'posts-list.html', context)


def contacts(request):
    # позже здесь будет код для статистики заходов на эту страницу
    # и для записи фидбека
    return render(request, 'contacts.html', {})
