from rest_framework import serializers



class LegalRegistrationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.ImageField()
    banner = serializers.ImageField()
    description = serializers.CharField()
    eligibility = serializers.CharField()
    required_documents = serializers.CharField()
    web_links = serializers.CharField()
    mode_of_application = serializers.CharField()

