from rest_framework import serializers

from lineup.models import ScheduleGame, GameParticipant


class GameParticipantSerializer(serializers.ModelSerializer):

    class Meta:
        model = GameParticipant
        fields = (
            'discord_user_id',
            'name',
            'status'
        )


class ScheduleGameSerializer(serializers.ModelSerializer):
    participants = GameParticipantSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField(
        method_name='get_tags',
    )

    class Meta:
        model = ScheduleGame
        fields = (
            'discord_thread_id',
            'name',
            'tags',
            'created_at',
            'participants',
        )

    def get_tags(self, obj):
        tags = obj.tags
        list_tags = []
        for tag in tags.split(', '):
            list_tags.append(tag)
        return list_tags
