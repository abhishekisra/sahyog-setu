from rest_framework import serializers

class StateSerializer(serializers.Serializer):
    value = serializers.IntegerField(source="id")
    label = serializers.CharField(source="state")
    