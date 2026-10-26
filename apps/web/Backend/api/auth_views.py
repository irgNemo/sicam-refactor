"""Session entry points and institutional administration; no public registration."""
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, mixins, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import OperationalPermission, ScopedViewMixin, ScopedSerializerMixin, operational, profile_for, scoped
from .models import (Institution, SicamUserProfile, MuestraSaliva, MuestraSangre,
                     CalibrationReference, ImageJImportRecord)

User = get_user_model()


def user_data(user):
    profile = profile_for(user)
    institution = profile.institution if profile else None
    return dict(id=user.pk, username=user.username, first_name=user.first_name, last_name=user.last_name,
                email=user.email, is_active=user.is_active, is_superuser=user.is_superuser,
                institution=InstitutionSerializer(institution).data if institution else None,
                role=profile.role if profile else None,
                must_change_password=profile.must_change_password if profile else False,
                last_login=user.last_login, date_joined=user.date_joined)


class AuthContext(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = get_token(request)
        if not operational(request.user, password_change=True):
            return Response({'user': None, 'csrf_token': token}, status=200)
        return Response({'user': user_data(request.user), 'csrf_token': token})


class LoginInput(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class PasswordInput(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)
    confirmation = serializers.CharField(trim_whitespace=False, write_only=True)


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        values = LoginInput(data=request.data)
        values.is_valid(raise_exception=True)
        user = authenticate(request=request, **values.validated_data)
        if not operational(user, password_change=True):
            raise PermissionDenied('Credenciales o acceso no válidos.')
        login(request, user)
        return Response({'user': user_data(user), 'csrf_token': get_token(request)})


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({'user': None, 'csrf_token': get_token(request)})


class PasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not operational(request.user, password_change=True):
            raise PermissionDenied()
        values = PasswordInput(data=request.data)
        values.is_valid(raise_exception=True)
        current = values.validated_data['current_password']
        password = values.validated_data['new_password']
        if not request.user.check_password(current):
            raise ValidationError({'current_password': 'Contraseña actual incorrecta.'})
        if not password or password != request.data.get('confirmation') or password == current:
            raise ValidationError({'new_password': 'Use una contraseña nueva y confirme el mismo valor.'})
        try:
            validate_password(password, request.user)
        except DjangoValidationError as exc:
            raise ValidationError({'new_password': exc.messages})
        with transaction.atomic():
            request.user.set_password(password)
            request.user.save(update_fields=['password'])
            SicamUserProfile.objects.filter(user=request.user).update(must_change_password=False)
        update_session_auth_hash(request, request.user)
        # Invalidate the cached OneToOne after the conditional metadata update.
        request.user.refresh_from_db()
        return Response({'user': user_data(request.user), 'csrf_token': get_token(request)})


class InstitutionSerializer(serializers.ModelSerializer):
    operational_summary = serializers.SerializerMethodField()

    def get_operational_summary(self, instance):
        # Session bootstrap and ordinary operational readers receive no admin metrics.
        request = self.context.get('request')
        if not request or not operational(request.user) or not (request.user.is_superuser or profile_for(request.user).role == 'ADMIN'):
            return None
        from .models import Paciente, AcquisitionProfile, Calibration, AcquisitionSeries
        profiles = SicamUserProfile.objects.filter(institution=instance)
        return dict(active_admins=profiles.filter(role='ADMIN', user__is_active=True).count(),
                    active_users=profiles.filter(user__is_active=True).count(),
                    patients=Paciente.objects.filter(institution=instance).count(),
                    archived_patients=Paciente.objects.filter(institution=instance, archived_at__isnull=False).count(),
                    profiles=AcquisitionProfile.objects.filter(institution=instance).count(),
                    calibrations=Calibration.objects.filter(acquisition_profile__institution=instance).count(),
                    series=AcquisitionSeries.objects.filter(patient__institution=instance).count())

    class Meta:
        model = Institution
        fields = ['id', 'code', 'name', 'active', 'notes', 'created_at', 'updated_at', 'operational_summary']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        if self.instance and self.instance.active and attrs.get('active') is False and self.initial_data.get('confirm_deactivation') is not True:
            raise ValidationError({'active': 'Desactivar impide operar a todos los usuarios de esta institución, incluidas sesiones abiertas. Confirme con confirm_deactivation=true.'})
        return attrs

    def validate_code(self, value):
        if self.instance and self.instance.code != value:
            raise ValidationError('El código institucional es estable.')
        return value


class InstitutionViewSet(ScopedViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                         mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = Institution.objects.order_by('pk')
    serializer_class = InstitutionSerializer


class UserSerializer(ScopedSerializerMixin, serializers.ModelSerializer):
    institution = serializers.PrimaryKeyRelatedField(queryset=Institution.objects.filter(active=True), required=False)
    role = serializers.ChoiceField(choices=['ADMIN', 'OPERATOR', 'REVIEWER'], required=False)
    temporary_password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    confirmation = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'role',
                  'institution', 'temporary_password', 'confirmation']
        read_only_fields = ['id']

    def to_representation(self, instance):
        return user_data(instance)

    def validate(self, attrs):
        actor = self.context['request'].user
        if any(key in self.initial_data for key in ('is_staff', 'is_superuser', 'groups', 'user_permissions', 'password', 'must_change_password')):
            raise ValidationError('No se admite elevar privilegios ni alterar credenciales por esos campos.')
        old = profile_for(self.instance) if self.instance else None
        if self.instance and self.instance.is_superuser:
            raise ValidationError('Las cuentas de plataforma se gestionan mediante Django, fuera de esta API.')
        tenant = attrs.get('institution', old.institution if old else None)
        if not actor.is_superuser:
            own = actor.sicam_profile.institution
            if tenant and tenant != own:
                raise ValidationError({'institution': 'Institución no permitida.'})
            tenant = own
        if not tenant or not tenant.active:
            raise ValidationError({'institution': 'Se requiere una institución activa.'})
        if old and old.institution != tenant:
            raise ValidationError({'institution': 'No se permite reasignar usuarios a otra institución.'})
        attrs['institution'] = tenant
        attrs['role'] = attrs.get('role', old.role if old else 'OPERATOR')
        password = attrs.pop('temporary_password', None)
        confirmation = attrs.pop('confirmation', None)
        if not self.instance and not password:
            raise ValidationError({'temporary_password': 'Obligatoria.'})
        if self.instance and password is not None:
            raise ValidationError({'temporary_password': 'La contraseña se cambia desde la sesión del usuario.'})
        if password is not None:
            if password != confirmation:
                raise ValidationError({'confirmation': 'Las contraseñas no coinciden.'})
            candidate = User(**{key: attrs.get(key, '') for key in ('username', 'first_name', 'last_name', 'email')})
            try:
                validate_password(password, candidate)
            except DjangoValidationError as exc:
                raise ValidationError({'temporary_password': exc.messages})
            attrs['temporary_password'] = password
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tenant, role = validated_data.pop('institution'), validated_data.pop('role')
        password = validated_data.pop('temporary_password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        SicamUserProfile.objects.create(user=user, institution=tenant, role=role, must_change_password=True)
        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        tenant = validated_data.pop('institution')
        # Serialize administrator changes for this institution, including the last-admin check.
        Institution.objects.select_for_update().get(pk=tenant.pk)
        instance = User.objects.select_for_update().get(pk=instance.pk)
        profile = SicamUserProfile.objects.select_for_update().get(user=instance)
        role = validated_data.pop('role')
        active = validated_data.get('is_active', instance.is_active)
        if not self.context['request'].user.is_superuser and profile.role == 'ADMIN' and instance.is_active and (role != 'ADMIN' or not active):
            if not SicamUserProfile.objects.filter(institution=tenant, role='ADMIN', user__is_active=True).exclude(user=instance).exists():
                raise ValidationError('No se puede desactivar ni degradar al último ADMIN activo.')
        profile.role = role
        profile.save(update_fields=['role', 'updated_at'])
        return super().update(instance, validated_data)


class UserViewSet(ScopedViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                  mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.select_related('sicam_profile__institution').order_by('pk')
    serializer_class = UserSerializer


class PrivateMediaView(APIView):
    permission_classes = [OperationalPermission]

    def get(self, request, kind, pk):
        model, field = {'saliva': (MuestraSaliva, 'imagen'), 'sangre': (MuestraSangre, 'imagen'),
                        'calibration': (CalibrationReference, 'source_image'),
                        'imagej-mask': (ImageJImportRecord, 'source_mask_file')}.get(kind, (None, None))
        if not model:
            raise Http404
        obj = get_object_or_404(scoped(model.objects.all(), request.user), pk=pk)
        file = getattr(obj, field)
        if not file:
            raise Http404
        from django.conf import settings
        if settings.PRIVATE_MEDIA_DELIVERY == 'nginx':
            from pathlib import Path
            from urllib.parse import quote
            from django.http import HttpResponse
            from django.utils.http import content_disposition_header
            import mimetypes
            try:
                root = Path(settings.MEDIA_ROOT).resolve()
                path = Path(file.path).resolve(strict=True)
                relative = path.relative_to(root)
                if not path.is_file():
                    raise Http404
            except (OSError, ValueError, NotImplementedError):
                raise Http404
            response = HttpResponse(content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            response['X-Accel-Redirect'] = '/_sicam_private_media/' + quote(relative.as_posix(), safe='/')
            response['Content-Disposition'] = content_disposition_header(False, path.name)
        else:
            try:
                response = FileResponse(file.open('rb'), as_attachment=False)
            except OSError:
                raise Http404
        response['Cache-Control'] = 'private, no-store'
        response['Vary'] = 'Cookie'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
