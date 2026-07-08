from rest_framework import serializers

class TestimonialSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.ImageField()
    