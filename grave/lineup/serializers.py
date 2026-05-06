from rest_framework import serializers

from lineup.models import ScheduleGame, GameParticipant, GameCellAssignment


class GameParticipantSerializer(serializers.ModelSerializer):

    class Meta:
        model = GameParticipant
        fields = (
            'id',
            'discord_user_id',
            'name',
            'status'
        )


class GameCellAssignmentSerializer(serializers.ModelSerializer):
    participant_id = serializers.PrimaryKeyRelatedField(
        source='participant',
        read_only=True
    )

    class Meta:
        model = GameCellAssignment
        fields = ['participant_id', 'cell_index', 'page_number', 'role_icon', 'vehicle_icon', 'vehicle_color']


class ScheduleGameSerializer(serializers.ModelSerializer):
    participants = GameParticipantSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField(
        method_name='get_tags',
    )
    assignments = GameCellAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = ScheduleGame
        fields = (
            'id',
            'discord_thread_id',
            'name',
            'tags',
            'game_format',
            'game_map',
            'created_at',
            'game_start_time',
            'participants',
            'assignments'
        )

    def get_tags(self, obj):
        tags = obj.tags
        list_tags = []
        for tag in tags.split(', '):
            list_tags.append(tag)
        return list_tags
