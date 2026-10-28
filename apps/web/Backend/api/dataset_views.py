"""Authenticated, tenant-scoped Dataset Builder. No live scientific calculations."""
import copy
import csv
import io
import json
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .services.datasets.xlsx import workbook
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .access import OperationalPermission, scoped
from .models import MLDataset, MLDatasetPatient, MLDatasetSample, Paciente, Institution
from .patient_lookup import patient_identity
from .services.datasets.features import FEATURES, UNAVAILABLE, SPLIT_WARNING
from .services.datasets.builder import build_snapshot, manifest
from .services.datasets.classes import validate_assignments
from .services.lifecycle import conflict


class MembershipInput(serializers.Serializer):
    patient_id = serializers.IntegerField(min_value=1)
    class_label = serializers.CharField(max_length=100,allow_blank=True)


class DefinitionInput(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    description = serializers.CharField(max_length=4000,allow_blank=True,default='')
    institution = serializers.IntegerField(min_value=1,required=False)
    characterization_version = serializers.ChoiceField(choices=['2.1','2.2'])
    units_mode = serializers.ChoiceField(choices=['PIXELS','PHYSICAL','BOTH'])
    features = serializers.ListField(child=serializers.ChoiceField(choices=[f['key'] for f in FEATURES]),allow_empty=False)
    classes = serializers.ListField(child=serializers.CharField(max_length=100, allow_blank=False), required=True)
    validated_only = serializers.BooleanField(default=True)
    patients = MembershipInput(many=True,allow_empty=True)
    version = serializers.IntegerField(min_value=1,required=False)

    def validate(self,data):
        if data['characterization_version']=='2.1' and data['units_mode']!='PIXELS':
            raise ValidationError('Characterization 2.1 no contiene snapshot físico.')
        for text in [data['name'],data['description'],*data['classes'],*[p['class_label'] for p in data['patients']]]:
            if any(not (ord(c) in (9,10,13) or 32<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD or 0x10000<=ord(c)<=0x10FFFF) for c in text):
                raise ValidationError('El texto contiene caracteres no exportables a Excel.')
        ids=[p['patient_id'] for p in data['patients']]
        if len(ids)>500 or len(set(ids))!=len(ids) or len(set(data['features']))!=len(data['features']):
            raise ValidationError('Selección duplicada o límite de 500 pacientes excedido.')
        data['classes'] = validate_assignments(data['classes'], data['patients'])
        return data


class DatasetPagination(PageNumberPagination):
    page_size=20


def readable_summary(snapshot):
    """Derive missing historical counters for responses, never rewrite snapshots."""
    summary = copy.deepcopy(snapshot['summary'])
    patients = snapshot['patients']
    summary.setdefault('selected_patient_count', len(patients))
    summary.setdefault('included_patient_count', sum(p['rows'] > 0 for p in patients))
    summary.setdefault('zero_row_patient_count', sum(p['rows'] == 0 for p in patients))
    for label, counts in summary['class_counts'].items():
        counts.setdefault('selected_patients', sum(p['Clase'] == label for p in patients))
        counts.setdefault('included_patients', sum(p['Clase'] == label and p['rows'] > 0 for p in patients))
        counts.setdefault('row_count', counts['rows'])
    return summary


def detail(obj):
    result={k:getattr(obj,k) for k in ['id','name','description','institution_id','status','dataset_type','characterization_version','units_mode',
      'config','created_by_id','created_at','generated_at','version','row_count','patient_count','sample_count','content_hash','manifest']}
    result['patients']=[{'patient_id':m.patient_id,'local_id':m.local_id,'class_label':m.class_label,'identity':patient_identity(m.patient) if m.patient.institution_id==obj.institution_id else {'id':m.patient_id,'initials':'','identificacion':''}} for m in obj.patients.all()]
    if obj.status=='GENERATED':result['summary']=readable_summary(obj.snapshot);result['exclusions']=obj.snapshot['exclusions']
    return result


def flatten_manifest(value, path=''):
    if isinstance(value,dict):
        return [row for k,v in value.items() for row in flatten_manifest(v,f'{path}.{k}' if path else k)]
    if isinstance(value,list):
        return [row for i,v in enumerate(value) for row in flatten_manifest(v,f'{path}[{i}]')]
    return [[path,excel_safe(value)]]


def excel_safe(value):
    if isinstance(value,bool):return int(value)
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):return "'"+value
    return value


class DatasetViewSet(viewsets.GenericViewSet):
    queryset=MLDataset.objects.all()
    permission_classes=[OperationalPermission]
    pagination_class=DatasetPagination
    serializer_class=DefinitionInput
    http_method_names=['get','post','put','head','options']

    def get_queryset(self):
        return scoped(self.queryset,self.request.user).prefetch_related('patients__patient').order_by('-created_at','pk')

    def list(self,request):
        page=self.paginate_queryset(self.get_queryset().prefetch_related(None).defer('snapshot','manifest','config').annotate(frozen_patients=F('snapshot__patients')))
        # Read only the small patient summary, including for historical snapshots.
        results=[]
        for d in page:
            item={k:getattr(d,k) for k in ['id','name','status','dataset_type','patient_count','row_count','characterization_version','units_mode','created_at','generated_at','created_by_id']}
            item['selected_patient_count']=d.patient_count
            item['included_patient_count']=sum(p['rows'] > 0 for p in d.frozen_patients) if d.status=='GENERATED' else None
            item['zero_row_patient_count']=d.patient_count-item['included_patient_count'] if d.status=='GENERATED' else None
            results.append(item)
        return self.get_paginated_response(results)

    def retrieve(self,request,pk=None):return Response(detail(self.get_object()))

    @action(detail=False,methods=['get'],url_path='options')
    def catalog(self,request):
        institutions=list(Institution.objects.filter(active=True).values('id','code')) if request.user.is_superuser else []
        return Response({'features':FEATURES,'versions':['2.1','2.2'],'unavailable':UNAVAILABLE,'split_warning':SPLIT_WARNING,'institutions':institutions})

    def definition(self,request,obj=None):
        serializer=DefinitionInput(data=request.data);serializer.is_valid(raise_exception=True);data=serializer.validated_data
        tenant_id=data.get('institution') if request.user.is_superuser else request.user.sicam_profile.institution_id
        if obj:
            if 'institution' in data and data['institution']!=obj.institution_id:raise ValidationError('La institución no puede cambiar.')
            tenant_id=obj.institution_id
        if not tenant_id:raise ValidationError('Seleccione una institución.')
        get_object_or_404(Institution,pk=tenant_id,active=True)
        if not request.user.is_superuser and data.get('institution',tenant_id)!=tenant_id:raise ValidationError('Institución no autorizada.')
        ids=[p['patient_id'] for p in data['patients']]
        found=list(scoped(Paciente.objects.all(),request.user).filter(pk__in=ids,institution_id=tenant_id).values_list('pk',flat=True))
        if set(ids)!=set(found):raise ValidationError('Selección de pacientes no autorizada.')
        return data,tenant_id

    def save_definition(self,obj,data):
        for key in ('name','description','characterization_version','units_mode'):setattr(obj,key,data[key])
        obj.config={'features':sorted(data['features']),'validated_only':data['validated_only'],'classes':data['classes']}
        obj.patient_count=len(data['patients']);obj.save()
        obj.patients.all().delete()
        MLDatasetPatient.objects.bulk_create([MLDatasetPatient(dataset=obj,patient_id=p['patient_id'],class_label=p['class_label'],local_id=f'P{i:03d}') for i,p in enumerate(sorted(data['patients'],key=lambda p:p['patient_id']),1)])
        return Response(detail(self.get_queryset().get(pk=obj.pk)))

    @transaction.atomic
    def create(self,request):
        data,tenant=self.definition(request)
        obj=MLDataset(institution_id=tenant,created_by=request.user)
        response=self.save_definition(obj,data);response.status_code=201;return response

    def lock_draft(self,request):
        obj=self.get_object()
        if obj.status!='DRAFT':conflict('GENERATED_DATASET_IMMUTABLE')
        version=request.data.get('version')
        if not isinstance(version,int) or isinstance(version,bool):raise ValidationError('Se requiere version del borrador.')
        if not MLDataset.objects.filter(pk=obj.pk,status='DRAFT',version=version).update(version=F('version')+1):conflict('DATASET_CHANGED')
        # Conditional update also obtains SQLite write lock before reading sources.
        return MLDataset.objects.get(pk=obj.pk)

    @transaction.atomic
    def update(self,request,pk=None):
        obj=self.lock_draft(request);data,_=self.definition(request,obj)
        return self.save_definition(obj,data)

    @action(detail=True,methods=['get'])
    def preview(self,request,pk=None):
        obj=self.get_object()
        snapshot,key=(obj.snapshot,obj.content_hash) if obj.status=='GENERATED' else build_snapshot(obj)
        return Response({'version':obj.version,'preview_hash':key,'summary':readable_summary(snapshot),'exclusions':snapshot['exclusions'],
           'patients':snapshot['patients'],'columns':snapshot['columns'],'sample_rows':snapshot['rows'][:10],
           'split_warning':SPLIT_WARNING,'characterization_version':obj.characterization_version,'units_mode':obj.units_mode,'validated_only':obj.config['validated_only']})

    @action(detail=True,methods=['post'])
    @transaction.atomic
    def generate(self,request,pk=None):
        if request.data.get('confirm') is not True:raise ValidationError('Confirme explícitamente la generación.')
        obj=self.lock_draft(request)
        if not Institution.objects.filter(pk=obj.institution_id,active=True).exists():raise ValidationError('Institución inactiva.')
        snapshot,key=build_snapshot(obj)
        if request.data.get('preview_hash')!=key:conflict('PREVIEW_CHANGED',detail='Los datos cambiaron. Obtenga una nueva vista previa.')
        if not snapshot['rows']:raise ValidationError('No quedan filas exportables.')
        now=timezone.now();obj.snapshot=snapshot;obj.manifest=manifest(obj,snapshot,key,now)
        obj.content_hash=key;obj.generated_at=now;obj.status='GENERATED'
        obj.row_count=snapshot['summary']['rows'];obj.sample_count=snapshot['summary']['samples'];obj.save()
        MLDatasetSample.objects.bulk_create([MLDatasetSample(dataset=obj,sample_id=s['sample_id'],characterization_id=s['source'].get('characterization_id'),local_id=s['local_id'],included=s['included'],reason=s['reason'],source_snapshot=s['source']) for s in snapshot['sources']])
        return Response(detail(self.get_queryset().get(pk=obj.pk)))

    @action(detail=True,methods=['get'],url_path='download/(?P<kind>csv|xlsx|manifest)')
    def download(self,request,pk=None,kind=None):
        obj=self.get_object()
        if obj.status!='GENERATED':raise ValidationError('Genere el snapshot antes de descargar.')
        snapshot=obj.snapshot
        rows=[[excel_safe(v) for v in row] for row in snapshot['rows']]
        if kind=='csv':
            stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');writer.writerow(snapshot['columns']);writer.writerows(rows)
            body=stream.getvalue().encode('utf-8');mime='text/csv; charset=utf-8';ext='csv'
        elif kind=='manifest':body=json.dumps(obj.manifest,ensure_ascii=False,indent=2).encode('utf-8');mime='application/json';ext='json'
        else:
            sheets=[('Datos',snapshot['columns'],rows),
              ('Pacientes',['ID_paciente','Clase','Muestras_incluidas','Filas','Estado_inclusion'],[[p[k] for k in ['ID_paciente','Clase','samples','rows']]+['INCLUIDO' if p['rows'] else 'SIN_DATOS_ELEGIBLES'] for p in snapshot['patients']]),
              ('Exclusiones',['patient','sample','reason','description'],[[p[k] for k in ['patient','sample','reason','description']] for p in snapshot['exclusions']]),
              ('Manifiesto',['Campo','Valor'],flatten_manifest(obj.manifest))]
            body=workbook([(name,headers,[[excel_safe(v) for v in row] for row in items]) for name,headers,items in sheets])
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';ext='xlsx'
        response=HttpResponse(body,content_type=mime);response['Content-Disposition']=f'attachment; filename="dataset-{obj.pk}.{ext}"'
        response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff';return response
