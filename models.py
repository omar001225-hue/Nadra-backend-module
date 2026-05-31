from django.db import models
from django.utils import timezone

from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Office


class CrowdSnapshot(models.Model):
    CROWD_STATUS_LOW = 'Low'
    CROWD_STATUS_MODERATE = 'Moderate'
    CROWD_STATUS_CROWDED = 'Crowded'

    CROWD_STATUS_CHOICES = [
        (CROWD_STATUS_LOW, 'Low'),
        (CROWD_STATUS_MODERATE, 'Moderate'),
        (CROWD_STATUS_CROWDED, 'Crowded'),
    ]

    snapshot_id = models.AutoField(primary_key=True)
    office = models.ForeignKey(
        Office,
        on_delete=models.CASCADE,
        related_name='crowd_snapshots'
    )
    captured_at = models.DateTimeField(default=timezone.now)
    people_count = models.PositiveIntegerField()
    crowd_status = models.CharField(
        max_length=10,
        choices=CROWD_STATUS_CHOICES
    )
    image = models.ImageField(
        upload_to='crowd_images/',
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'CrowdSnapshot'
        ordering = ['-captured_at']
        verbose_name = 'Crowd Snapshot'
        verbose_name_plural = 'Crowd Snapshots'

    def __str__(self):
        return (
            f"{self.office.branch_name} - {self.crowd_status} "
            f"({self.people_count}) at {self.captured_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )



@receiver(post_save, sender=CrowdSnapshot)
def trigger_admin_refresh(sender, instance, created, **kwargs):
    if created:
        # This forces the Office to "touch" its record and refresh the Admin view
        instance.office.save()