from rest_framework import serializers

class CategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.ImageField()
    banner = serializers.ImageField()
    


class SchemeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    banner = serializers.ImageField()
    scheme_type = serializers.IntegerField()
    status = serializers.IntegerField()
    income_min = serializers.IntegerField()
    income_max = serializers.IntegerField()
    divyang = serializers.IntegerField()
    description = serializers.CharField()
    eligibility = serializers.CharField()
    required_documents = serializers.CharField()
    web_links = serializers.CharField()
    mode_of_application = serializers.CharField()
    occupations = serializers.CharField()
    age_max = serializers.IntegerField()
    age_min = serializers.IntegerField()
    scheme_for = serializers.CharField()
    state=serializers.CharField(source = "state.state", default="")
    marital_status = serializers.CharField()
    benificiaries = serializers.CharField()
    religions = serializers.CharField()
    castes = serializers.CharField()

