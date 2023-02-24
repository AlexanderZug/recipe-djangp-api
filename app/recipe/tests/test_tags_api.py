from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Tag,
    Recipe,
)

from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """Return tag detail URL."""
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='test@test.com', password='testpass'):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(email=email, password=password)


def sample_tag(user, name='Main course'):
    """Create and return a sample tag."""
    return Tag.objects.create(user=user, name=name)


class PublicTagsApiTests(TestCase):
    """Test the publicly available tags API."""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required for retrieving tags."""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test the authorized user tags API."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving tags."""
        sample_tag(user=self.user)
        sample_tag(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test that tags returned are for the authenticated user."""
        user2 = create_user(email='user@test2.com', password='testpass2')
        sample_tag(user=user2, name='Fruity')
        tags = sample_tag(user=self.user, name='Comfort food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tags.name)
        self.assertEqual(res.data[0]['id'], tags.id)

    def test_update_tag(self):
        """Test updating a tag."""
        tag = sample_tag(user=self.user)
        payload = {'name': 'New name'}

        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test deleting a tag."""
        tag = sample_tag(user=self.user)
        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(id=tag.id)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test returning tags that are assigned to recipes."""
        tag1 = sample_tag(user=self.user, name='Breakfast')
        tag2 = sample_tag(user=self.user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Eggs on toast',
            time_minutes=10,
            price=Decimal('5.00'),
            user=self.user,
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        serializer1 = TagSerializer(tag1)
        serializer2 = TagSerializer(tag2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_tags_assigned_unique(self):
        """Test filtering tags by assigned returns unique items."""
        tag = sample_tag(user=self.user, name='Breakfast')
        sample_tag(user=self.user, name='Lunch')
        recipe1 = Recipe.objects.create(
            title='Pancakes',
            time_minutes=5,
            price=Decimal('3.00'),
            user=self.user,
        )
        recipe1.tags.add(tag)
        recipe2 = Recipe.objects.create(
            title='Porridge',
            time_minutes=3,
            price=Decimal('2.00'),
            user=self.user,
        )
        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
