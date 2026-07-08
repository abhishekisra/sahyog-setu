from rest_framework import serializers

class HelplinesSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.ImageField()
    link = serializers.CharField()
    title = serializers.CharField()
    color = serializers.CharField()
    