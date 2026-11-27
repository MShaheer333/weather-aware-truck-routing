from rest_framework import serializers

from .services.analysis import ALLOWED_INTERVALS


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(required=False, allow_blank=True, max_length=300, default="")


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = LocationSerializer()
    destination = LocationSerializer()
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.FloatField(min_value=0, max_value=150_000)
    checkpoint_interval_miles = serializers.ChoiceField(choices=ALLOWED_INTERVALS, default=25)

    def validate_checkpoint_interval_miles(self, value):
        return int(value)
