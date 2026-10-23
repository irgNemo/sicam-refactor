"""Single operational policy, tenant scopes and serializer admission boundary."""
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import permissions, serializers

ROLES = {'ADMIN', 'OPERATOR', 'REVIEWER'}
WRITE_ROLES = {
    'paciente': {'ADMIN', 'OPERATOR'}, 'caso': {'ADMIN', 'OPERATOR'},
    'analisispred': {'ADMIN', 'OPERATOR'}, 'muestrasaliva': {'ADMIN', 'OPERATOR'},
    'muestrasangre': {'ADMIN', 'OPERATOR'}, 'acquisitionseries': {'ADMIN', 'OPERATOR'},
    'acquisitionprofile': {'ADMIN'}, 'calibration': {'ADMIN'}, 'calibrationreference': {'ADMIN'},
    'revisionsegmentacion': ROLES, 'resultadosegmentacion': ROLES,
    'user': {'ADMIN'}, 'institution': set(),
}
PATHS = {
    'institution': 'pk', 'sicamuserprofile': 'institution_id', 'user': 'sicam_profile__institution_id',
    'paciente': 'institution_id', 'caso': 'paciente__institution_id',
    'analisispred': 'id_paciente_fk__institution_id',
    'muestrasaliva': 'analisis__id_paciente_fk__institution_id',
    'muestrasangre': 'analisis__id_paciente_fk__institution_id',
    'acquisitionprofile': 'institution_id', 'calibration': 'acquisition_profile__institution_id',
    'calibrationreference': 'calibration__acquisition_profile__institution_id',
    'acquisitionseries': 'patient__institution_id', 'imagejimportrecord': 'paciente__institution_id',
}


def profile_for(user):
    try:
        return user.sicam_profile
    except (ObjectDoesNotExist, AttributeError):
        return None


def operational(user, *, password_change=False):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    profile = profile_for(user)
    if user.is_superuser:
        return password_change or not profile or not profile.must_change_password
    return bool(profile and profile.role in ROLES and profile.institution.active
                and (password_change or not profile.must_change_password))


def scoped(queryset, user):
    if not operational(user):
        return queryset.none()
    if user.is_superuser:
        return queryset
    tenant = user.sicam_profile.institution_id
    model = queryset.model._meta.model_name
    path = PATHS.get(model)
    if path:
        return queryset.filter(**{path: tenant})
    prefix = {'revisionsegmentacion': 'resultado_segmentacion__',
              'resultadocaracterizacion': 'resultado_segmentacion__',
              'resultadosegmentacion': ''}.get(model)
    if prefix is not None:
        return queryset.filter(Q(**{prefix+'muestra__analisis__id_paciente_fk__institution_id': tenant}) |
                               Q(**{prefix+'muestra_sangre__analisis__id_paciente_fk__institution_id': tenant}))
    return queryset.none()  # New domain models fail closed until mapped explicitly.


class OperationalPermission(permissions.BasePermission):
    message = 'La sesión no permite esta operación.'

    def has_permission(self, request, view):
        if not operational(request.user):
            return False
        if request.user.is_superuser:
            return True
        # Institutional destructive operations require the lifecycle policy in 18T-B.
        if request.method == 'DELETE':
            return False
        role = request.user.sicam_profile.role
        model = getattr(getattr(view, 'queryset', None), 'model', None)
        name = model._meta.model_name if model else ''
        if request.method in permissions.SAFE_METHODS:
            return name != 'user' or role == 'ADMIN'
        action = getattr(view, 'action', '')
        if action == 'validar':
            return role in {'ADMIN', 'REVIEWER'}
        if action == 'segmentar':
            return role in ROLES
        return role in WRITE_ROLES.get(name, set())


class ScopedViewMixin:
    permission_classes = [OperationalPermission]

    def get_queryset(self):
        return scoped(super().get_queryset(), self.request.user)


class ScopedSerializerMixin:
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        for name, field in fields.items():
            if name in ('created_by', 'updated_by'):
                field.read_only = True
                field.required = False
            elif request and getattr(field, 'queryset', None) is not None:
                field.queryset = scoped(field.queryset.all(), request.user)
        return fields

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        request = self.context.get('request')
        model = getattr(getattr(self, 'Meta', None), 'model', None)
        if request and model and model._meta.model_name in ('paciente', 'acquisitionprofile'):
            institution = attrs.get('institution', getattr(self.instance, 'institution', None))
            if not request.user.is_superuser:
                own = request.user.sicam_profile.institution
                if institution and institution != own:
                    raise serializers.ValidationError({'institution': 'Institución no permitida.'})
                institution = own
            if self.instance and institution is None and request.user.is_superuser:
                return attrs
            if not institution or not institution.active:
                raise serializers.ValidationError({'institution': 'Seleccione una institución activa.'})
            if self.instance and institution.pk != self.instance.institution_id:
                raise serializers.ValidationError({'institution': 'El ownership no se reasigna por API.'})
            attrs['institution'] = institution
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(self.Meta.model, 'created_by'):
            validated_data.update(created_by=request.user, updated_by=request.user)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and hasattr(instance, 'updated_by'):
            validated_data['updated_by'] = request.user
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        result = super().to_representation(instance)
        for name in ('created_by', 'updated_by'):
            if name in result:
                author = getattr(instance, name, None)
                result[name] = ({'id': author.pk, 'username': author.username,
                                 'display_name': author.get_full_name() or author.username} if author else None)
        model = instance._meta.model_name
        field, kind = {'muestrasaliva': ('imagen', 'saliva'), 'muestrasangre': ('imagen', 'sangre'),
                       'calibrationreference': ('source_image', 'calibration')}.get(model, (None, None))
        if field and getattr(instance, field):
            from django.urls import reverse
            url = reverse('private-media', args=[kind, instance.pk])
            request = self.context.get('request')
            result[field] = request.build_absolute_uri(url) if request else url
        return result
