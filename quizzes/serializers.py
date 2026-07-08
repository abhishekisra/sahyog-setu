from rest_framework import serializers

class QuestionSerializer(serializers.Serializer):
    # correct_option deliberately excluded — this serializer feeds the
    # pre-attempt "get quiz questions" API, so shipping the answer key
    # here would let anyone read it before taking the quiz. Scoring now
    # happens server-side in quiz_submit_api (see views mobile submit).
    id = serializers.IntegerField()
    question = serializers.CharField()
    option_1 = serializers.CharField()
    option_2 = serializers.CharField()
    option_3 = serializers.CharField()
    option_4 = serializers.CharField()


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