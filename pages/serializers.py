from rest_framework import serializers

class PageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    image = serializers.ImageField()