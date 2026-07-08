from rest_framework import serializers

class QuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    question = serializers.CharField()
    option_1 = serializers.CharField()
    option_2 = serializers.CharField()
    option_3 = serializers.CharField()
    option_4 = serializers.CharField()
    correct_option = serializers.IntegerField()
    

class QuizzesSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    image = serializers.ImageField()
    created_at = serializers.DateTimeField()
    total_questions = serializers.IntegerField()
    quiz_time = serializers.IntegerField()

class QuizSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    image = serializers.ImageField()
    created_at = serializers.DateTimeField()
    total_questions = serializers.IntegerField()
    questions = QuestionSerializer(many=True)
    quiz_time = serializers.IntegerField()