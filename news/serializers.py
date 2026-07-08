from rest_framework import serializers

class NewsSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    news = serializers.CharField()
    link = serializers.CharField()