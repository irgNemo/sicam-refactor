"""Operational lifecycle metadata; default managers deliberately retain history."""
from django.conf import settings
from django.db import models


class ArchivableModel(models.Model):
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='+')
    archive_reason = models.TextField(blank=True, default='')

    class Meta:
        abstract = True


class LifecycleEvent(models.Model):
    institution = models.ForeignKey('api.Institution', null=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    action = models.CharField(max_length=24, choices=[(v, v) for v in ('ARCHIVE', 'RESTORE', 'HARD_DELETE', 'RETIRE')])
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    target_display = models.CharField(max_length=160)
    reason = models.TextField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
