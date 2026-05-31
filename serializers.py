from rest_framework import serializers

from .models import CrowdSnapshot
from accounts.models import Office


class CrowdCaptureSerializer(serializers.Serializer):
    office = serializers.PrimaryKeyRelatedField(
        queryset=Office.objects.all()
    )
    image = serializers.ImageField(required=False, allow_null=True)
    people_count = serializers.IntegerField(required=False, min_value=0)
    crowd_status = serializers.CharField(required=False)

    def validate(self, data):
        image = data.get('image')
        people_count = data.get('people_count')
        crowd_status = data.get('crowd_status')

        if image:
            return data

        if people_count is None or crowd_status is None:
            raise serializers.ValidationError(
                'Either provide an image or both people_count and crowd_status.'
            )

        valid_statuses = [choice[0] for choice in CrowdSnapshot.CROWD_STATUS_CHOICES]
        if crowd_status not in valid_statuses:
            raise serializers.ValidationError(
                {'crowd_status': f"crowd_status must be one of {valid_statuses}."}
            )

        return data


class CrowdSnapshotSerializer(serializers.ModelSerializer):
    office_name = serializers.CharField(source='office.branch_name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = CrowdSnapshot
        fields = [
            'snapshot_id',
            'office',
            'office_name',
            'captured_at',
            'people_count',
            'crowd_status',
            'image_url',
        ]
        read_only_fields = [
            'snapshot_id',
            'captured_at',
            'people_count',
            'crowd_status',
            'image_url',
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request is not None:
            return request.build_absolute_uri(obj.image.url)
        if obj.image:
            return obj.image.url
        return None
