from rest_framework import serializers



class SchemeAnnouncementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.ImageField()
    link = serializers.CharField()

