from django.contrib import admin

from .models import CrowdSnapshot


@admin.register(CrowdSnapshot)
class CrowdSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'snapshot_id',
        'office',
        'people_count',
        'crowd_status',
        'captured_at',
    )
    list_filter = ('crowd_status', 'office', 'captured_at')
    search_fields = ('office__branch_name',)
    readonly_fields = ('captured_at',)
