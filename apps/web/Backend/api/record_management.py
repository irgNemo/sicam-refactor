"""Private paginated record views and explicit, transactional historical association."""
import hashlib
import json
from pathlib import PurePosixPath

from django.core import signing
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from django.db.models import Count, Q, Value, CharField
from django.shortcuts import get_object_or_404
from PIL import Image
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import OperationalPermission, scoped
from .patient_lookup import search_patients, patient_identity, patient_label
from .models import Paciente, Caso, MuestraSaliva, MuestraSangre, AcquisitionSeries
from .services.acquisition import physical_compatibility
from .services.lifecycle import request_queryset, active_queryset, lock_operational, validate_binding, is_operationally_active, conflict

SAMPLES = {'SALIVA': MuestraSaliva, 'SANGRE': MuestraSangre}
SALT = 'sicam.historical-series.v1'


def integer(params, key, default=None):
    value = params.get(key, default)
    if value is None or value == '':
        return None
    if not str(value).isdigit() or int(value) < 1:
        raise ValidationError({key: 'Identificador o página inválidos.'})
    return int(value)


def series_data(series):
    profile, cal = series.acquisition_profile, series.calibration
    return {'id': series.pk, 'label': series.label, 'patient_id': series.patient_id,
            'profile': {'id': profile.pk, 'name': profile.name,
                        'objective': str(profile.objective_magnification or ''),
                        'width': profile.image_width_px, 'height': profile.image_height_px,
                        'mode': profile.image_mode},
            'calibration': {'id': cal.pk, 'label': cal.label, 'status': cal.status} if cal else None}


def sample_queryset(model, request):
    return request_queryset(scoped(model.objects.all(), request.user), request).select_related(
        'analisis__id_paciente_fk', 'analisis__id_caso_fk__paciente',
        'acquisition_series__patient', 'acquisition_series__acquisition_profile',
        'acquisition_series__calibration').annotate(
            characterization_count=Count('resultados_segmentacion__caracterizaciones', distinct=True))


def sample_data(sample, kind):
    series = sample.acquisition_series
    compatibility = physical_compatibility(sample, series=series, patient_id=sample.analisis.id_paciente_fk_id)
    dimensions = compatibility.get('source_dimensions')
    mode = None
    try:
        with sample.imagen.storage.open(sample.imagen.name, 'rb') as f, Image.open(f) as image:
            dimensions = {'width': image.width, 'height': image.height}; mode = image.mode
    except (OSError, ValueError, Image.DecompressionBombError):
        pass
    return {'id': sample.pk, 'type': kind, 'resource': 'muestras' if kind == 'SALIVA' else 'muestras-sangre',
            'filename': PurePosixPath(sample.imagen.name).name,
            'patient_id': sample.analisis.id_paciente_fk_id,
            'patient': patient_label(sample.analisis.id_paciente_fk),
            'patient_identity': patient_identity(sample.analisis.id_paciente_fk),
            'case_id': sample.analisis.id_caso_fk_id, 'analysis_id': sample.analisis_id,
            'dimensions': dimensions, 'mode': mode,
            'series': series_data(series) if series else None, 'compatibility': compatibility,
            'characterization_count': sample.characterization_count,
            'archived': not is_operationally_active(sample)}


class RecordManagementView(APIView):
    permission_classes = [OperationalPermission]

    def get(self, request, resource):
        page = integer(request.query_params, 'page', 1); size = 20
        search = request.query_params.get('search', '').strip()[:150]
        patient = integer(request.query_params, 'patient')
        case = integer(request.query_params, 'case')
        start, end = (page - 1) * size, page * size
        if resource in ('patients', 'cases'):
            model = Paciente if resource == 'patients' else Caso
            qs = request_queryset(scoped(model.objects.all(), request.user), request)
            if resource == 'patients':
                qs = qs.annotate(case_count=Count('casos', distinct=True),
                    saliva_count=Count('analisis__muestras_saliva', distinct=True),
                    blood_count=Count('analisis__muestras_sangre', distinct=True))
                if search:
                    qs = search_patients(qs, search)
            else:
                qs = qs.select_related('paciente').annotate(analysis_count=Count('analisis', distinct=True),
                    saliva_count=Count('analisis__muestras_saliva', distinct=True),
                    blood_count=Count('analisis__muestras_sangre', distinct=True))
                if patient: qs = qs.filter(paciente_id=patient)
                if search: qs = qs.filter(pk=int(search) if search.isdigit() else -1)
            count = qs.count(); rows = []
            for obj in qs.order_by('pk')[start:end]:
                row = {'id': obj.pk, 'label': patient_label(obj) if resource == 'patients' else f'Caso #{obj.pk}',
                       'archived': not is_operationally_active(obj), 'image_count': obj.saliva_count + obj.blood_count}
                if resource == 'patients': row.update(**patient_identity(obj), case_count=obj.case_count)
                else: row.update(patient_id=obj.paciente_id, patient=patient_label(obj.paciente), patient_identity=patient_identity(obj.paciente), analysis_count=obj.analysis_count)
                rows.append(row)
        elif resource == 'images':
            kinds = request.query_params.get('type', '')
            if kinds and kinds not in SAMPLES: raise ValidationError({'type': 'Tipo inválido.'})
            queries = {}
            series_filter = request.query_params.get('series', '')
            for kind, model in SAMPLES.items():
                if kinds and kind != kinds: continue
                qs = sample_queryset(model, request)
                if patient: qs = qs.filter(analisis__id_paciente_fk_id=patient)
                if case: qs = qs.filter(analisis__id_caso_fk_id=case)
                if search: qs = qs.filter(Q(imagen__icontains=search) | Q(pk=int(search) if search.isdigit() else -1))
                if series_filter == 'none': qs = qs.filter(acquisition_series__isnull=True)
                elif series_filter: qs = qs.filter(acquisition_series_id=integer(request.query_params, 'series'))
                queries[kind] = qs
            # UNION only IDs; fetch the current page with related objects in two queries.
            ids = [q.order_by().annotate(kind=Value(k, output_field=CharField())).values('pk', 'kind') for k,q in queries.items()]
            combined = ids[0] if len(ids) == 1 else ids[0].union(*ids[1:])
            count = combined.count(); selected = list(combined.order_by('kind', 'pk')[start:end])
            objects = {(k,o.pk):o for k,q in queries.items() for o in q.filter(pk__in=[x['pk'] for x in selected if x['kind']==k])}
            rows = [sample_data(objects[(x['kind'],x['pk'])], x['kind']) for x in selected]
        else:
            raise ValidationError({'resource': 'Vista desconocida.'})
        return Response({'count': count, 'page': page, 'page_size': size, 'results': rows})


class SeriesOptionsView(APIView):
    permission_classes = [OperationalPermission]

    def get(self, request):
        patient = integer(request.query_params, 'patient')
        if not patient: raise ValidationError({'patient': 'Seleccione un paciente.'})
        get_object_or_404(active_queryset(scoped(Paciente.objects.all(), request.user)), pk=patient)
        qs = active_queryset(scoped(AcquisitionSeries.objects.all(), request.user)).filter(
            patient_id=patient, patient__institution__active=True, acquisition_profile__active=True, acquisition_profile__archived_at__isnull=True,
            acquisition_profile__institution_id=Paciente.objects.get(pk=patient).institution_id,
        ).exclude(calibration__status='RETIRED').select_related('acquisition_profile','calibration')
        return Response([series_data(s) for s in qs.order_by('pk')])


class SampleRef(serializers.Serializer):
    type = serializers.ChoiceField(choices=list(SAMPLES))
    id = serializers.IntegerField(min_value=1)


class AssignmentInput(serializers.Serializer):
    series_id = serializers.IntegerField(min_value=1)
    samples = SampleRef(many=True, allow_empty=False, max_length=50)
    confirm = serializers.BooleanField(default=False)
    preview_token = serializers.CharField(required=False, default='')


class AssignSeriesView(APIView):
    permission_classes = [OperationalPermission]
    queryset = MuestraSaliva.objects.none()  # Reuse existing ADMIN/OPERATOR write policy.

    @transaction.atomic
    def post(self, request, operation):
        if operation not in ('preview', 'assign'): raise ValidationError('Operación inválida.')
        payload = AssignmentInput(data=request.data); payload.is_valid(raise_exception=True)
        data = payload.validated_data
        refs = sorted({(x['type'],x['id']) for x in data['samples']})
        if len(refs) != len(data['samples']): raise ValidationError('Selección duplicada.')
        series = get_object_or_404(scoped(AcquisitionSeries.objects.all(), request.user), pk=data['series_id'])
        validate_binding(series)
        series = lock_operational(series)
        validate_binding(series.acquisition_profile)
        if series.calibration_id: validate_binding(series.calibration)
        samples = []
        for kind, pk in refs:
            obj = get_object_or_404(scoped(SAMPLES[kind].objects.all(), request.user), pk=pk)
            samples.append((kind, lock_operational(obj)))
        patients = {s.analisis.id_paciente_fk_id for _,s in samples}
        if len(patients) != 1:
            conflict('MIXED_PATIENTS', detail='Las imágenes seleccionadas pertenecen a pacientes diferentes. Selecciona imágenes de un solo paciente para asignarlas a una serie.')
        if patients != {series.patient_id}: conflict('PATIENT_MISMATCH')
        tenant = series.patient.institution_id
        if not tenant or not series.patient.institution.active or tenant != series.acquisition_profile.institution_id:
            conflict('INSTITUTION_MISMATCH')
        if any(s.analisis.id_paciente_fk.institution_id != tenant for _,s in samples): conflict('INSTITUTION_MISMATCH')
        rows, source = [], []
        for kind,sample in samples:
            old = sample.acquisition_series_id
            if old and old != series.pk: conflict('SERIES_ALREADY_ASSIGNED', detail='Esta imagen ya pertenece a otra serie.')
            source.append([kind, sample.pk, sample.imagen.name])
            sample.acquisition_series = series  # In-memory candidate only during preview.
            rows.append({'id':sample.pk, 'type':kind, 'already_assigned':old == series.pk,
                         'compatibility': physical_compatibility(sample)})
        context = {'samples':source, 'rows':[{k:v for k,v in row.items() if k != 'already_assigned'} for row in rows], 'series': list(AcquisitionSeries.objects.filter(pk=series.pk).values()),
                   'profile': list(type(series.acquisition_profile).objects.filter(pk=series.acquisition_profile_id).values()),
                   'calibration': list(type(series.calibration).objects.filter(pk=series.calibration_id).values()) if series.calibration else []}
        digest = hashlib.sha256(json.dumps(context,sort_keys=True,default=str).encode()).hexdigest()
        output = {'series':series_data(series), 'results':rows,
                  'compatible_count':sum(r['compatibility']['compatible_for_physical_units'] for r in rows)}
        if operation == 'preview':
            output['preview_token'] = signing.dumps({'digest':digest,'user':request.user.pk}, salt=SALT)
            return Response(output)
        if not data['confirm']: raise ValidationError({'confirm':'Confirme explícitamente la asociación.'})
        try: token = signing.loads(data['preview_token'], salt=SALT, max_age=600)
        except signing.BadSignature: conflict('PREVIEW_EXPIRED')
        if token != {'digest':digest,'user':request.user.pk}: conflict('PREVIEW_CHANGED')
        for (_, sample), row in zip(samples, rows):
            if row['already_assigned']: continue
            sample.updated_by = request.user
            try: sample.save(update_fields=['acquisition_series','updated_by'])
            except ModelValidationError as exc: raise ValidationError(exc.messages)
        return Response(output)
