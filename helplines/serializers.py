from rest_framework import serializers

class HelplinesSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.ImageField()
    link = serializers.CharField()
    title = serializers.CharField()
    color = serializers.CharField()
    number = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    