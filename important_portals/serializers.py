from rest_framework import serializers



class ImportantPortalSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.ImageField()
    banner = serializers.ImageField()
    description = serializers.CharField()
    mode_of_application = serializers.CharField()

