from rest_framework import serializers

class OccupationSerializer(serializers.Serializer):
    value = serializers.IntegerField(source="id")
    label = serializers.CharField(source="title")
    