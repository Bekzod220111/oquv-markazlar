from rest_framework import serializers
from .models import Subject, Center, Course, CenterImage, Review


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name", "slug"]


class CourseSerializer(serializers.ModelSerializer):
    category = SubjectSerializer(read_only=True)

    class Meta:
        model = Course
        fields = ["id", "name", "alternative_names", "category", "price_min", "price_max", "description", "duration"]


class CenterImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenterImage
        fields = ["id", "image", "alt"]


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "author", "rating", "text", "created_at"]


class CenterSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)
    distance_km = serializers.FloatField(read_only=True)
    courses = CourseSerializer(many=True, read_only=True)
    images = CenterImageSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Center
        fields = [
            "id", "name", "description", "phone", "address",
            "latitude", "longitude", "rating", "price_monthly", "price_min", "price_max", "image_url",
            "subjects", "distance_km", "alternative_names", "email", "website", "instagram",
            "telegram", "working_hours", "is_active", "courses", "images", "reviews",
        ]
