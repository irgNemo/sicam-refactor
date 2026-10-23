"""Operational identity; independent of clinical external identity."""
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models


class Institution(models.Model):
    id = models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name="ID")
    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            old = type(self).objects.filter(pk=self.pk).values('code').first()
            if old and old['code'] != self.code:
                raise ValidationError({'code': 'El código institucional es estable.'})
        return super().save(*args, **kwargs)


class SicamUserProfile(models.Model):
    id = models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name="ID")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sicam_profile')
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT)
    role = models.CharField(max_length=12, choices=[(v, v) for v in ('ADMIN', 'OPERATOR', 'REVIEWER')])
    must_change_password = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(role__in=['ADMIN', 'OPERATOR', 'REVIEWER']), name='sicam_valid_role')]


class AuthoredModel(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            old = type(self).objects.filter(pk=self.pk).values('created_by_id').first()
            if old and old['created_by_id'] != self.created_by_id:
                raise ValidationError({'created_by': 'La autoría original es inmutable.'})
        return super().save(*args, **kwargs)

    class Meta:
        abstract = True
