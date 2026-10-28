import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from django.db.models import Prefetch
from rest_framework.exceptions import ValidationError
from api.models import MuestraSaliva, ResultadoSegmentacion, RevisionSegmentacion, ResultadoCaracterizacion
from api.services.segmentation.effective import resolve_effective_segmentation
from .classes import validate_assignments
from .features import columns, CORE, SCHEMA_VERSION, GRAIN, SPLIT_WARNING

REASONS = {
 'ARCHIVED':'Paciente, caso, análisis o muestra archivados.',
 'NO_CHARACTERIZATION':'Sin caracterización guardada.',
 'CHARACTERIZATION_VERSION_MISMATCH':'No existe la versión solicitada.',
 'SEGMENTATION_NOT_VALIDATED':'La segmentación no cumple la política de validación.',
 'NO_EFFECTIVE_SEGMENTATION':'No hay resultado efectivo completo.',
 'SOURCE_CHANGED':'La caracterización no corresponde a la segmentación efectiva.',
 'SOURCE_UNVERIFIABLE':'Resultado automático antiguo sin hash de segmentación verificable.',
 'NO_PHYSICAL_VALUES':'Faltan valores físicos almacenados requeridos.',
 'CALIBRATION_INCOMPATIBLE':'El snapshot físico no declara compatibilidad.',
 'INVALID_CHARACTERIZATION':'Estructura/relaciones duplicadas o inválidas.',
 'NO_NUCLEI':'No contiene núcleos exportables.',
 'RELATIONSHIP_MISMATCH':'La relación paciente/caso de la muestra es inconsistente.',
}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def metric(obj, path):
    value = (obj or {}).get('metrics',{})
    for key in path.split('.'):
        value = value.get(key) if isinstance(value,dict) else None
    if value is None: return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Invalid numeric feature')
    return value


def relations(data):
    """Use only persisted nucleus_id edges. Unassociated nuclei retain a negative row."""
    nuclei, edges, mn_ids = {}, defaultdict(list), set()
    def add_nucleus(n):
        if n.get('id') is None or n['id'] in nuclei: raise ValueError('Duplicate nucleus ID')
        nuclei[n['id']] = n
    for cell in data['cells']:
        cell_ids=set()
        for n in cell['nuclei']: add_nucleus(n);cell_ids.add(n['id'])
        for mn in cell['micronuclei']:
            if mn.get('id') is None or mn['id'] in mn_ids: raise ValueError('Duplicate MN ID')
            mn_ids.add(mn['id'])
            if mn.get('nucleus_id') is None: continue
            if mn['nucleus_id'] not in cell_ids: raise ValueError('Broken association')
            edges[mn['nucleus_id']].append(mn)
    for group in ('unassociated','ambiguous'):
        for n in data.get(group,{}).get('nuclei',[]): add_nucleus(n)
    return [(nuclei[key], sorted(edges[key],key=lambda x:str(x['id']))) for key in sorted(nuclei,key=str)]


def source_info(c, effective):
    data=c.resultado_json
    calibration=data.get('calibration') or {}
    return {'characterization_id':c.pk,'version':c.algorithm_version,'source_type':c.source_type,
            'revision_id':c.revision_segmentacion_id,'segmentation_result_id':c.resultado_segmentacion_id,
            'fingerprint':data.get('provenance',{}).get('fingerprint'),
            'characterization_json_sha256':digest(data),
            'effective_segmentation_hash':digest(effective['resultado']),
            'stored_effective_segmentation_hash':data.get('provenance',{}).get('effective_segmentation_hash'),
            'physical_status':data.get('physical_status'),'calibration':{k:calibration.get(k) for k in
              ('calibration_id','status','scale_x_um_per_px','scale_y_um_per_px','acquisition_profile_id','acquisition_series_id')},
            'texture_methodology':data.get('methodology',{}).get('texture',{})}


def build_snapshot(dataset):
    members=list(dataset.patients.select_related('patient').order_by('patient_id'))
    if not members or any(not m.class_label.strip() for m in members):
        raise ValidationError('Seleccione pacientes y asigne una clase a cada uno.')
    if any(m.patient.institution_id!=dataset.institution_id for m in members):
        raise ValidationError('PATIENT_INSTITUTION_CHANGED')
    assignments = [{'class_label': m.class_label} for m in members]
    validate_assignments(dataset.config.get('classes', []), assignments, require_complete=True)
    if any(m.class_label != p['class_label'] for m, p in zip(members, assignments)):
        raise ValidationError('Guarde el borrador para normalizar las clases antes de generar.')
    cmap={m.patient_id:m for m in members}
    chars=ResultadoCaracterizacion.objects.filter(sample_type='SALIVA').order_by('-created_at','-pk')
    revisions=RevisionSegmentacion.objects.filter(estado='VALIDADA').order_by('-numero_revision')
    results=ResultadoSegmentacion.objects.filter(tipo_muestra='SALIVA').order_by('-pk').prefetch_related(
        Prefetch('revisiones',queryset=revisions,to_attr='validated_revisions_for_effective'),
        Prefetch('caracterizaciones',queryset=chars,to_attr='dataset_characterizations'))
    samples=MuestraSaliva.objects.filter(analisis__id_paciente_fk_id__in=cmap).select_related(
        'analisis__id_caso_fk','analisis__id_paciente_fk').order_by('analisis__id_paciente_fk_id','pk').prefetch_related(
        Prefetch('resultados_segmentacion',queryset=results,to_attr='dataset_results'))
    selected=columns(dataset.config,dataset.units_mode)
    rows=[];sources=[];exclusions=[];counts=Counter();balance={};patient_summary=[];nuclei_count=0;mn_count=0;provisional=0;sample_ord=Counter()
    for m in members:
        balance.setdefault(m.class_label,{'patients':0,'rows':0,'samples':0})['patients']+=1
    for sample in samples:
        member=cmap[sample.analisis.id_paciente_fk_id];pid=member.local_id
        sample_ord[pid]+=1;sid=f'{pid}_IMG{sample_ord[pid]:03d}'
        reason='';char=None;info={};batch=[];nuclei=[];row_excluded=0
        parents=[member.patient,sample.analisis,sample.analisis.id_caso_fk,sample]
        result=sample.dataset_results[0] if sample.dataset_results else None
        if sample.analisis.id_caso_fk and sample.analisis.id_caso_fk.paciente_id!=member.patient_id:reason='RELATIONSHIP_MISMATCH'
        elif any(getattr(p,'archived_at',None) for p in parents): reason='ARCHIVED'
        elif not result or result.estado!='COMPLETADO' or not result.resultado_normalizado: reason='NO_EFFECTIVE_SEGMENTATION'
        else:
            effective=resolve_effective_segmentation(result)
            if effective['fuente']=='MANUAL' or (dataset.config['validated_only'] and effective['fuente']!='VALIDADA'): reason='SEGMENTATION_NOT_VALIDATED'
            else:
                exact=[c for c in result.dataset_characterizations if c.algorithm_version==dataset.characterization_version]
                if not exact: reason='CHARACTERIZATION_VERSION_MISMATCH' if result.dataset_characterizations else 'NO_CHARACTERIZATION'
                else:
                    revision=(effective.get('revision') or {}).get('id_revision_segmentacion')
                    matching=[c for c in exact if c.source_type==effective['fuente'] and c.revision_segmentacion_id==revision and
                              (not c.resultado_json.get('provenance',{}).get('effective_segmentation_hash') or
                               c.resultado_json['provenance']['effective_segmentation_hash']==digest(effective['resultado']))]
                    if not matching:reason='SOURCE_CHANGED'
                    else:char=matching[0]
            if char:
                data=char.resultado_json;info=source_info(char,effective)
                if char.source_type=='AUTOMATICO' and not info['stored_effective_segmentation_hash']:reason='SOURCE_UNVERIFIABLE'
                elif data.get('version')!=dataset.characterization_version or data.get('sample_type')!='SALIVA':reason='INVALID_CHARACTERIZATION'
                elif dataset.units_mode!='PIXELS':
                    if not data.get('physical_units_available'):reason='NO_PHYSICAL_VALUES'
                    elif data.get('physical_status') not in ('COMPATIBLE','COMPATIBLE_PROVISIONAL'):reason='CALIBRATION_INCOMPATIBLE'
                if not reason:
                    try:
                        nuclei=relations(data)
                        for ni,(n,mns) in enumerate(nuclei,1):
                            nid=f'{sid}_N{ni:03d}'
                            for mi,mn in enumerate(mns or [None],1):
                                values=[metric(n if f['entity']=='nucleus' else mn,f['path']) for f in selected]
                                if dataset.units_mode!='PIXELS' and (metric(n,'area_um2') is None or
                                   any(f['physical_column'] and v is None and (f['entity']=='nucleus' or mn is not None) for f,v in zip(selected,values))):
                                    row_excluded+=1;continue
                                batch.append([pid,sid,nid,f'{nid}_MN{mi:03d}' if mn else None,member.class_label,bool(mn),*values])
                        if not batch:reason='NO_PHYSICAL_VALUES' if row_excluded else 'NO_NUCLEI'
                    except (KeyError,TypeError,ValueError):reason='INVALID_CHARACTERIZATION';batch=[]
        if reason:
            counts[reason]+=1;exclusions.append({'patient':pid,'sample':sid,'reason':reason,'description':REASONS[reason]})
        else:
            rows.extend(batch);nuclei_count+=len({r[2] for r in batch});mn_count+=sum(r[5] for r in batch)
            balance[member.class_label]['rows']+=len(batch);balance[member.class_label]['samples']+=1
            if info.get('calibration',{}).get('status')=='PROVISIONAL':provisional+=1
            if row_excluded:exclusions.append({'patient':pid,'sample':sid,'reason':'NO_PHYSICAL_VALUES','description':f'{row_excluded} relaciones excluidas por valores físicos nulos.','rows':row_excluded})
        sources.append({'sample_id':sample.pk,'local_id':sid,'patient':pid,'included':not bool(reason),'reason':reason,'source':info})
        if len(rows)>100000:raise ValidationError('Límite síncrono de 100000 filas excedido. Reduzca la selección.')
    for m in members:
        patient_summary.append({'ID_paciente':m.local_id,'Clase':m.class_label,
          'samples':sum(s['included'] and s['patient']==m.local_id for s in sources),
          'rows':sum(r[0]==m.local_id for r in rows)})
    for label, counts_by_class in balance.items():
        counts_by_class['selected_patients'] = counts_by_class['patients']
        counts_by_class['included_patients'] = sum(p['Clase'] == label and p['rows'] > 0 for p in patient_summary)
        counts_by_class['row_count'] = counts_by_class['rows']
    included = sum(p['rows'] > 0 for p in patient_summary)
    summary={'selected_patient_count':len(members),'included_patient_count':included,
      'zero_row_patient_count':len(members)-included,'patients':len(members),'samples':sum(s['included'] for s in sources),'excluded_samples':sum(not s['included'] for s in sources),
      'rows':len(rows),'nuclei':nuclei_count,'mn_associations':mn_count,'class_counts':balance,'provisional_count':provisional,
      'exclusion_counts':dict(counts),'excluded_rows':sum(e.get('rows',0) for e in exclusions),
      'calibration_status_counts':dict(Counter(s['source'].get('calibration',{}).get('status') or 'NONE' for s in sources if s['included']))}
    snapshot={'schema_version':SCHEMA_VERSION,'columns':CORE+[f['column'] for f in selected],'rows':rows,'sources':sources,
      'patients':patient_summary,'exclusions':exclusions,'summary':summary,
      'configuration':{'characterization_version':dataset.characterization_version,'units_mode':dataset.units_mode,'config':dataset.config,
                       'membership':[{'patient_id':m.patient_id,'local_id':m.local_id,'class_label':m.class_label} for m in members]}}
    return snapshot,digest(snapshot)


def manifest(dataset,snapshot,key,now):
    return {'dataset_id':str(dataset.pk),'name':dataset.name,'schema_version':SCHEMA_VERSION,
       'created_at':dataset.created_at.isoformat(),'generated_at':now.isoformat(),'created_by_id':dataset.created_by_id,
       'institution_id':dataset.institution_id,'dataset_type':dataset.dataset_type,'row_grain':GRAIN,
       **snapshot['summary'],'characterization_version':dataset.characterization_version,'units_mode':dataset.units_mode,
       'features':dataset.config['features'],'filters':{'validated_only':dataset.config['validated_only'],'archived':'EXCLUDE'},
       'source_policy':'latest stored exact-version result matching current effective segmentation; freeze rows at generation',
       'sources':[{'image':s['local_id'],'included':s['included'],'reason':s['reason'],**s['source']} for s in snapshot['sources']],
       'content_hash':key,'null_representation':'empty cell','numeric_format':'decimal point',
       'split_group':'patient','split_applied':False,'split_warning':SPLIT_WARNING,
       'GLCM_PHYSICAL_DISTANCE_NORMALIZATION':'PENDING; texture remains in pixel domain',
       'provisional_warning':'Las unidades físicas incluyen resultados basados en calibración provisional.' if snapshot['summary']['provisional_count'] and dataset.units_mode!='PIXELS' else None}
