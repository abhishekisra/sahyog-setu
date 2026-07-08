from rest_framework import serializers



class BusinessPlanSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.ImageField()
    pdf = serializers.FileField()