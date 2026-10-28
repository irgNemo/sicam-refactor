"""Synthetic stored results only: no live data or scientific engine execution."""
import copy
import csv
import io
import json
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from api.models import (Institution,SicamUserProfile,Paciente,Caso,AnalisisPred,MuestraSaliva,
 ResultadoSegmentacion,RevisionSegmentacion,ResultadoCaracterizacion,MLDataset,MLDatasetSample,LifecycleEvent)
from api.services.datasets.builder import digest


def metrics():
    return {'area_px2':20,'perimeter_px':18,'area_um2':.2,'perimeter_um':1.8,'eccentricity':.5,'circularity':.7,
       'mean_gray_intensity':12.5,'std_gray_intensity':2.5,'texture':{'contrast':1.2,'homogeneity':.3,'energy':.4,'correlation':.8}}


def result_json(counts,version='2.2',physical=True):
    nuclei=[{'id':i+1,'metrics':metrics()} for i in range(len(counts))]
    mns=[{'id':100+i*10+j,'nucleus_id':i+1,'metrics':{**metrics(),'area_fraction_to_nucleus':.05,'distance_to_nucleus_px':4,'distance_to_nucleus_um':.4}} for i,n in enumerate(counts) for j in range(n)]
    return {'version':version,'sample_type':'SALIVA','cells':[{'nuclei':nuclei,'micronuclei':mns}],
      'unassociated':{'nuclei':[],'micronuclei':[]},'ambiguous':{'nuclei':[],'micronuclei':[]},
      'physical_units_available':physical,'physical_status':'COMPATIBLE_PROVISIONAL' if physical else 'NO_ACQUISITION_SERIES',
      'calibration':{'calibration_id':1,'status':'PROVISIONAL','scale_x_um_per_px':'0.1','scale_y_um_per_px':'0.1'}}


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DatasetTests(TestCase):
    def setUp(self):
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup);media=override_settings(MEDIA_ROOT=tmp.name);media.enable();self.addCleanup(media.disable)
        self.tenant=Institution.objects.create(code='DATA_TEST',name='Synthetic');self.other=Institution.objects.create(code='OTHER_TEST',name='Synthetic')
        self.users={}
        for role in ['ADMIN','OPERATOR','REVIEWER']:
            user=get_user_model().objects.create_user(role);SicamUserProfile.objects.create(user=user,institution=self.tenant,role=role,must_change_password=False);self.users[role]=user
        self.client=APIClient();self.client.force_authenticate(self.users['ADMIN'])
        self.p1=self.patient('HIDDEN-A');self.p2=self.patient('HIDDEN-B');self.foreign=self.patient('HIDDEN-C',self.other)
        self.s1,self.r1,self.c1=self.sample(self.p1,[0,1]);self.s2,self.r2,self.c2=self.sample(self.p2,[3])
        self.data={'name':'Synthetic experiment','description':'','characterization_version':'2.2','units_mode':'PIXELS',
          'classes':['Class A','Class B'],'features':['nucleus_area','nucleus_eccentricity','area_ratio','centroid_distance'],'validated_only':True,
          'patients':[{'patient_id':self.p1.pk,'class_label':'Class A'},{'patient_id':self.p2.pk,'class_label':'Class B'}]}

    def patient(self,key,tenant=None):
        return Paciente.objects.create(institution=tenant or self.tenant,nombre='PRIVATE_NAME',apellido='PRIVATE_SURNAME',fecha_nacimiento='2000-01-01',identificacion=key,initials='EJT')

    def sample(self,patient,counts,version='2.2',validated=True,physical=True):
        case=Caso.objects.create(paciente=patient,titulo='PRIVATE_CASE');a=AnalisisPred.objects.create(id_paciente_fk=patient,id_caso_fk=case)
        sample=MuestraSaliva.objects.create(analisis=a,imagen='synthetic-not-read.jpg')
        base={'objects':[{'id':1,'label':'nucleo'}]}
        result=ResultadoSegmentacion.objects.create(muestra=sample,tipo_muestra='SALIVA',respuesta_json={},resultado_normalizado=base,estado='COMPLETADO')
        rev=RevisionSegmentacion.objects.create(resultado_segmentacion=result,numero_revision=1,estado='VALIDADA',resultado_editado=base,resumen={},validado_en=timezone.now()) if validated else None
        data=result_json(counts,version,physical);data['provenance']={'effective_segmentation_hash':digest(base),'fingerprint':'stored-test-fingerprint'}
        char=ResultadoCaracterizacion.objects.create(resultado_segmentacion=result,revision_segmentacion=rev,source_type='VALIDADA' if validated else 'AUTOMATICO',sample_type='SALIVA',algorithm_version=version,resultado_json=data)
        return sample,result,char

    def create(self,data=None):
        response=self.client.post('/api/datasets/',data or self.data,format='json');self.assertEqual(response.status_code,201,response.data);return response.data
    def preview(self,d):return self.client.get(f"/api/datasets/{d['id']}/preview/")
    def generate(self,d):
        p=self.preview(d);self.assertEqual(p.status_code,200,p.data)
        return self.client.post(f"/api/datasets/{d['id']}/generate/",{'confirm':True,'version':p.data['version'],'preview_hash':p.data['preview_hash']},format='json')

    def test_rows_zero_one_three_mn_are_five_not_cartesian(self):
        d=self.create();p=self.preview(d);self.assertEqual(p.data['summary']['rows'],5);self.assertEqual(p.data['summary']['nuclei'],3);self.assertEqual(p.data['summary']['mn_associations'],4)
        self.assertEqual(p.data['summary']['class_counts']['Class B']['rows'],3)
        r=self.generate(d);self.assertEqual(r.status_code,200,r.data);o=MLDataset.objects.get(pk=d['id']);self.assertEqual(o.row_count,5)
        self.assertIsNone(o.snapshot['rows'][0][3]);self.assertEqual([x[4] for x in o.snapshot['rows']],['Class A']*2+['Class B']*3)
        self.assertEqual(MLDatasetSample.objects.filter(dataset=o).count(),2);self.assertEqual(LifecycleEvent.objects.count(),0)

    def test_no_patients_missing_classes_and_zero_rows_cannot_generate(self):
        for patients in [[],[{'patient_id':self.p1.pk,'class_label':''}]]:
            d=self.create({**self.data,'patients':patients});self.assertEqual(self.preview(d).status_code,400)
        self.p1.archived_at=timezone.now();self.p1.save();self.p2.archived_at=timezone.now();self.p2.save()
        d=self.create();self.assertEqual(self.preview(d).data['summary']['rows'],0);self.assertEqual(self.generate(d).status_code,400)
        self.assertFalse(MLDataset.objects.filter(status='GENERATED').exists())

    def test_physical_both_snapshot_provisional_and_missing(self):
        for mode in ['PIXELS','PHYSICAL','BOTH']:
            d=self.create({**self.data,'units_mode':mode});p=self.preview(d).data
            self.assertEqual(p['summary']['rows'],5);self.assertEqual(p['summary']['provisional_count'],2)
            self.assertEqual('Area_um2' in p['columns'],mode!='PIXELS');self.assertEqual('Area_px2' in p['columns'],mode!='PHYSICAL')
        self.c1.resultado_json['physical_units_available']=False;self.c1.save()
        d=self.create({**self.data,'units_mode':'BOTH'});p=self.preview(d).data
        self.assertEqual(p['summary']['rows'],3);self.assertEqual(p['summary']['exclusion_counts']['NO_PHYSICAL_VALUES'],1)
        generated=self.generate(d);self.assertEqual(generated.status_code,200);self.assertIn('provisional',generated.data['manifest']['provisional_warning'])

    def test_versions_are_exact_and_21_physical_rejected(self):
        d=self.create({**self.data,'characterization_version':'2.1'});self.assertEqual(self.preview(d).data['summary']['exclusion_counts']['CHARACTERIZATION_VERSION_MISMATCH'],2)
        response=self.client.post('/api/datasets/',{**self.data,'characterization_version':'2.1','units_mode':'BOTH'},format='json');self.assertEqual(response.status_code,400)
        self.sample(self.p1,[0],version='2.1');self.assertEqual(self.preview(d).data['summary']['rows'],1)

    def test_validation_policy_draft_not_effective_and_source_changes(self):
        sample,result,char=self.sample(self.p1,[0],validated=False)
        RevisionSegmentacion.objects.create(resultado_segmentacion=result,numero_revision=1,estado='BORRADOR',resultado_editado={'objects':[]},resumen={})
        d=self.create();self.assertEqual(self.preview(d).data['summary']['exclusion_counts']['SEGMENTATION_NOT_VALIDATED'],1)
        d2=self.create({**self.data,'validated_only':False});self.assertEqual(self.preview(d2).data['summary']['rows'],6)
        result.resultado_normalizado={'objects':[{'id':99}]};result.save();self.assertEqual(self.preview(d2).data['summary']['exclusion_counts']['SOURCE_CHANGED'],1)

    def test_immutability_and_new_characterization_no_silent_substitution(self):
        d=self.create();self.assertEqual(self.generate(d).status_code,200)
        before=self.client.get(f"/api/datasets/{d['id']}/download/csv/").content
        for key,value in [('units_mode','BOTH'),('patients',[]),('features',['nucleus_perimeter']),('validated_only',False),('characterization_version','2.1')]:
            r=self.client.put(f"/api/datasets/{d['id']}/",{**self.data,key:value,'version':2},format='json');self.assertEqual(r.status_code,409)
        data=copy.deepcopy(self.c1.resultado_json);data['cells'][0]['nuclei'][0]['metrics']['area_px2']=999
        ResultadoCaracterizacion.objects.create(resultado_segmentacion=self.r1,revision_segmentacion=self.c1.revision_segmentacion,source_type='VALIDADA',sample_type='SALIVA',algorithm_version='2.2',resultado_json=data)
        self.assertEqual(before,self.client.get(f"/api/datasets/{d['id']}/download/csv/").content)
        self.assertIn(self.client.delete(f"/api/datasets/{d['id']}/").status_code,[403,405])

    def test_stale_preview_requires_new_confirmation_and_rolls_back(self):
        d=self.create();p=self.preview(d).data;self.c1.resultado_json['cells'][0]['nuclei'][0]['metrics']['area_px2']=21;self.c1.save()
        r=self.client.post(f"/api/datasets/{d['id']}/generate/",{'confirm':True,'version':p['version'],'preview_hash':p['preview_hash']},format='json')
        self.assertEqual(r.status_code,409);o=MLDataset.objects.get(pk=d['id']);self.assertEqual(o.status,'DRAFT');self.assertEqual(o.version,1);self.assertEqual(o.samples.count(),0)
        self.assertEqual(self.generate(d).status_code,200)

    def test_cross_tenant_role_and_superuser_policy(self):
        d=self.create()
        for role in ['OPERATOR','REVIEWER']:
            self.client.force_authenticate(self.users[role]);self.assertEqual(self.client.get('/api/datasets/').status_code,200)
            r=self.client.post('/api/datasets/',self.data,format='json');self.assertEqual(r.status_code,201 if role=='OPERATOR' else 403)
        self.assertEqual(self.generate(d).status_code,403)
        foreign=get_user_model().objects.create_user('foreign');SicamUserProfile.objects.create(user=foreign,institution=self.other,role='ADMIN',must_change_password=False)
        self.client.force_authenticate(foreign);self.assertEqual(self.client.get(f"/api/datasets/{d['id']}/").status_code,404)
        self.assertEqual(self.client.get('/api/datasets/').data['count'],0)
        self.client.force_authenticate(self.users['ADMIN']);self.assertEqual(self.client.post('/api/datasets/',{**self.data,'patients':[{'patient_id':self.foreign.pk,'class_label':'A'}]},format='json').status_code,400)
        superuser=get_user_model().objects.create_superuser('platform',password='synthetic');self.client.force_authenticate(superuser)
        self.assertEqual(self.client.get(f"/api/datasets/{d['id']}/").status_code,200)
        self.assertEqual(self.client.post('/api/datasets/',{**self.data,'institution':self.tenant.pk},format='json').status_code,201)

    def test_csv_xlsx_values_manifest_privacy_and_formula_safety(self):
        data=copy.deepcopy(self.data);data['patients'][0]['class_label']='=1+1';data['classes']=['=1+1','Class B'];d=self.create(data);self.assertEqual(self.generate(d).status_code,200)
        csv_body=self.client.get(f"/api/datasets/{d['id']}/download/csv/").content.decode();table=list(csv.reader(io.StringIO(csv_body)))
        xlsx=self.client.get(f"/api/datasets/{d['id']}/download/xlsx/").content
        with ZipFile(io.BytesIO(xlsx)) as z:
            ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'));actual=[]
            for row in root.findall('s:sheetData/s:row',ns):
                values=['']*len(table[0])
                for c in row.findall('s:c',ns):
                    letters=''.join(ch for ch in c.attrib['r'] if ch.isalpha());idx=0
                    for ch in letters:idx=idx*26+ord(ch)-64
                    text=c.find('s:is/s:t',ns) if c.attrib.get('t')=='inlineStr' else c.find('s:v',ns)
                    values[idx-1]=text.text or ''
                actual.append(values)
            self.assertEqual(actual,table);self.assertEqual(len(z.namelist()),9);self.assertIsNotNone(root.find('s:autoFilter',ns));self.assertFalse(root.findall('.//s:f',ns))
        self.assertEqual(table[1][4],"'=1+1")
        manifest=self.client.get(f"/api/datasets/{d['id']}/download/manifest/").json()
        self.assertEqual(manifest['split_group'],'patient');self.assertFalse(manifest['split_applied']);self.assertEqual(len(manifest['content_hash']),64)
        for secret in ['PRIVATE_NAME','PRIVATE_SURNAME','HIDDEN','2000-01-01','synthetic-not-read']:
            self.assertNotIn(secret,csv_body+json.dumps(manifest))
        self.client.force_authenticate(self.users['REVIEWER']);self.assertEqual(self.client.get(f"/api/datasets/{d['id']}/download/csv/").status_code,200)

    def test_hash_stable_preview_and_no_n_plus_one(self):
        d=self.create();first=self.preview(d).data['preview_hash'];self.assertEqual(first,self.preview(d).data['preview_hash'])
        with CaptureQueriesContext(connection) as one:self.preview(d)
        for _ in range(4):self.sample(self.p1,[0])
        with CaptureQueriesContext(connection) as many:self.preview(d)
        self.assertLessEqual(len(many),len(one)+1)

    def test_invalid_config_draft_update_and_generation_atomic(self):
        for change in [{'features':['Solidez']},{'patients':self.data['patients']*2},{'features':['nucleus_area']*2}]:
            self.assertEqual(self.client.post('/api/datasets/',{**self.data,**change},format='json').status_code,400)
        d=self.create();r=self.client.put(f"/api/datasets/{d['id']}/",{**self.data,'version':1,'name':'Changed'},format='json');self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.put(f"/api/datasets/{d['id']}/",{**self.data,'version':1},format='json').status_code,409)
        with patch('api.dataset_views.MLDatasetSample.objects.bulk_create',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):self.generate(r.data)
        o=MLDataset.objects.get(pk=d['id']);self.assertEqual(o.status,'DRAFT');self.assertEqual(o.version,2);self.assertEqual(o.samples.count(),0)

    def test_no_scientific_calls_and_null_rows_reported(self):
        self.c1.resultado_json['cells'][0]['nuclei'][0]['metrics']['area_um2']=None;self.c1.save()
        d=self.create({**self.data,'units_mode':'BOTH'})
        with patch('api.services.characterization.service.get_or_create_resultado_caracterizacion',side_effect=AssertionError('must not recalculate')),patch('api.services.acquisition.physical_compatibility',side_effect=AssertionError('must not use current calibration')):
            p=self.preview(d);self.assertEqual(p.data['summary']['rows'],4);self.assertEqual(p.data['summary']['excluded_rows'],1)
            self.assertEqual(self.generate(d).status_code,200)

    def test_invalid_relationship_and_missing_characterization_are_explained(self):
        self.c1.resultado_json['cells'][0]['micronuclei'][0]['nucleus_id']=999;self.c1.save();self.c2.delete()
        d=self.create();p=self.preview(d).data
        self.assertEqual(p['summary']['exclusion_counts'],{'INVALID_CHARACTERIZATION':1,'NO_CHARACTERIZATION':1})
        self.client.force_authenticate(None);self.assertIn(self.client.get('/api/datasets/').status_code,[401,403])

    def test_invalid_excel_text_and_options_metadata(self):
        self.assertEqual(self.client.post('/api/datasets/',{**self.data,'name':'bad\x00text'},format='json').status_code,400)
        self.assertEqual(self.client.options('/api/datasets/').status_code,200)
        self.assertEqual(self.client.get('/api/datasets/options/').status_code,200)

    def test_calibration_summary_and_no_cross_tenant_identity_after_patient_move(self):
        d=self.create();p=self.preview(d).data
        self.assertEqual(p['summary']['calibration_status_counts'],{'PROVISIONAL':2})
        # Synthetic administrative reassignment must not leak current identity
        # through an old draft; generation rejects the changed membership.
        Paciente.objects.filter(pk=self.p1.pk).update(institution=self.other)
        response=self.client.get(f"/api/datasets/{d['id']}/")
        self.assertEqual(response.status_code,200)
        self.assertNotIn('HIDDEN-A',json.dumps(response.data,default=str))
        self.assertEqual(self.preview(d).status_code,400)

    def test_class_catalog_normalization_and_assignment(self):
        data=copy.deepcopy(self.data)
        data['classes']=[' Diabetes+Ca ', 'Control']
        data['patients'][0]['class_label']=' DIABETES+CA '
        data['patients'][1]['class_label']='control'
        d=self.create(data)
        self.assertEqual(d['config']['classes'], ['Diabetes+Ca','Control'])
        self.assertEqual([p['class_label'] for p in d['patients']], ['Diabetes+Ca','Control'])
        self.assertEqual(self.generate(d).status_code,200)
        for classes in [['Clase 2',' clase 2 '],[''],['   '],['Straße','STRASSE']]:
            r=self.client.post('/api/datasets/',{**self.data,'classes':classes},format='json')
            self.assertEqual(r.status_code,400,r.data)
        self.assertIn('equivalente',str(self.client.post('/api/datasets/',{**self.data,'classes':['Class A',' class a ']},format='json').data))
        self.assertEqual(self.client.post('/api/datasets/',{**self.data,'classes':['Other']},format='json').status_code,400)
        data.pop('classes')
        self.assertEqual(self.client.post('/api/datasets/',data,format='json').status_code,400)

    def test_zero_row_counts_manifest_and_patient_export(self):
        data=copy.deepcopy(self.data)
        empty=self.patient('ZERO_PRIVATE')
        data['patients'].append({'patient_id':empty.pk,'class_label':'Class A'})
        d=self.create(data);preview=self.preview(d).data
        self.assertEqual([preview['summary'][k] for k in ('selected_patient_count','included_patient_count','zero_row_patient_count')],[3,2,1])
        self.assertEqual(preview['summary']['class_counts']['Class A']['selected_patients'],2)
        self.assertEqual(preview['summary']['class_counts']['Class A']['included_patients'],1)
        self.assertEqual(preview['summary']['class_counts']['Class A']['row_count'],2)
        r=self.generate(d);self.assertEqual(r.status_code,200)
        self.assertEqual(r.data['manifest']['zero_row_patient_count'],1)
        listed=self.client.get('/api/datasets/').data['results'][0]
        self.assertEqual(listed['included_patient_count'],2)
        xlsx=self.client.get(f"/api/datasets/{d['id']}/download/xlsx/").content
        with ZipFile(io.BytesIO(xlsx)) as z:
            ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            patient_xml=z.read('xl/worksheets/sheet2.xml').decode()
            self.assertIn('SIN_DATOS_ELEGIBLES',patient_xml)
            self.assertIn('P003',patient_xml)
            self.assertNotIn('ZERO_PRIVATE',patient_xml)
            self.assertNotIn('P003',z.read('xl/worksheets/sheet1.xml').decode())
            for i in range(1,5):
                sheet=ET.fromstring(z.read(f'xl/worksheets/sheet{i}.xml'))
                widths=sheet.findall('s:cols/s:col',ns)
                self.assertTrue(all(12<=float(c.attrib['width'])<=48 for c in widths))
                self.assertIsNotNone(sheet.find('s:sheetViews/s:sheetView/s:pane',ns))
                self.assertIsNotNone(sheet.find('s:autoFilter',ns))
                self.assertEqual(sheet.find('s:sheetData/s:row/s:c',ns).attrib['s'],'1')

    def test_historical_generated_classes_and_manifest_remain_readable(self):
        d=self.create();self.assertEqual(self.generate(d).status_code,200)
        obj=MLDataset.objects.get(pk=d['id'])
        old=copy.deepcopy(obj.snapshot);old['configuration']['config'].pop('classes')
        old['patients'][0]['Clase']='Clase 2';old['patients'][1]['Clase']='clase 2'
        for k in ('selected_patient_count','included_patient_count','zero_row_patient_count'):old['summary'].pop(k)
        historical_manifest={'patients':2,'content_hash':obj.content_hash}
        MLDataset.objects.filter(pk=obj.pk).update(snapshot=old,manifest=historical_manifest)
        response=self.client.get(f"/api/datasets/{obj.pk}/")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['summary']['included_patient_count'],2)
        self.assertEqual(self.preview(d).status_code,200)
        self.assertEqual(self.client.get(f"/api/datasets/{obj.pk}/download/manifest/").json(),historical_manifest)
        self.assertEqual(self.client.post(f"/api/datasets/{obj.pk}/generate/",{'confirm':True,'version':obj.version},format='json').status_code,409)
        obj.refresh_from_db();self.assertEqual(obj.snapshot,old);self.assertEqual(obj.manifest,historical_manifest)
