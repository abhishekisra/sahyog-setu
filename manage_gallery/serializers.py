from rest_framework import serializers



class ImageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.ImageField()



class VideoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    link = serializers.CharField()
