from rest_framework import serializers



class OrganizationRegistrationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.ImageField()
    banner = serializers.ImageField()
    pdf = serializers.FileField()
    description = serializers.CharField()
    mode_of_application = serializers.CharField()

