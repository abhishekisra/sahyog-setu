from rest_framework import serializers

class BannersSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.ImageField()

    