"""Synthetic ImageJ fixtures only; all files live in temporary directories."""
import copy
from datetime import date
from io import StringIO
from pathlib import Path
import tempfile
from unittest.mock import patch
from zipfile import ZipFile
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import (Paciente, Caso, AnalisisPred, MuestraSaliva, ResultadoSegmentacion,
                        RevisionSegmentacion, ResultadoCaracterizacion, ImageJImportRecord)
from api.serializers import PacienteSerializer
from api.services.imagej.contracts import ImportProblem, patient_key, sha256_path
from api.services.imagej.spreadsheet import read_patients, birth_date
from api.services.imagej.geometry import convert_pair, component_polygon, validate_contour
from api.services.imagej.importer import run_import, discover
from api.services.segmentation.effective import resolve_effective_segmentation


def xlsx(path, rows=None, adapter='standard'):
    headers = ['patient_key', 'patient_id', 'initials', 'birth_date'] if adapter == 'standard' else ['ID', 'Iniciales', 'Ignored', 'Fecha de nacimiento']
    rows = rows if rows is not None else [['ACL', '007', 'ACL', '2000-01-01']]
    all_rows = [headers, *rows] if adapter == 'standard' else [[''], headers, *rows]
    body = []
    for y, values in enumerate(all_rows, 1):
        cells = []
        for x, value in enumerate(values):
            ref = f'{chr(65+x)}{y}'
            if isinstance(value, int):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        body.append(f'<row r="{y}">{"".join(cells)}</row>')
    with ZipFile(path, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="patients" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(body)+'</sheetData></worksheet>')


class ImageJImportTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sicam-imagej-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.media = self.root/'media'
        self.settings = override_settings(MEDIA_ROOT=self.media)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.dataset = self.root/'dataset'
        self.folder = self.dataset/'pacientes'/'ACL'
        self.folder.mkdir(parents=True)
        self.excel = self.dataset/'pacientes.xlsx'
        xlsx(self.excel)
        self.image = self.folder/'sample.png'
        self.mask = self.folder/'sample.tif'
        Image.new('RGB', (40, 40), (127, 55, 10)).save(self.image)
        self.pixels = np.zeros((40, 40), dtype='uint8')
        self.pixels[4:12, 4:12] = 255
        self.pixels[20:24, 20:24] = 85
        Image.fromarray(self.pixels).save(self.mask)
        self.options = dict(source=self.dataset, patients_file=self.excel, dataset_key='test-case1', patient_namespace='test')
        self.client = APIClient()

    def run_import(self, **overrides):
        return run_import(**{**self.options, **overrides})

    def imported(self):
        report = self.run_import()
        self.assertEqual(report['errors'], 0, report)
        return ImageJImportRecord.objects.get()

    def files(self):
        return sorted(p.relative_to(self.media).as_posix() for p in self.media.rglob('*') if p.is_file())

    def test_identity_model_and_serializer(self):
        normal = Paciente(nombre='Synthetic', apellido='Fixture', fecha_nacimiento=date(2000,1,1), identificacion='legacy')
        normal.full_clean(); normal.save()
        self.assertEqual(normal.identity_mode, 'IDENTIFIED')
        for field in ('nombre', 'apellido'):
            serializer = PacienteSerializer(normal, data={field:''}, partial=True)
            self.assertFalse(serializer.is_valid())
        data = dict(identity_mode='PSEUDONYMIZED', external_id_namespace='test', external_patient_id='007', initials='ACL', fecha_nacimiento='2000-01-01', identificacion='pseudo')
        serializer = PacienteSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        pseudo = serializer.save()
        self.assertEqual((pseudo.nombre,pseudo.apellido), ('',''))
        self.assertEqual(pseudo.display_name,'ACL')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Paciente.objects.create(**{k:getattr(pseudo,k) for k in ['identity_mode','external_id_namespace','external_patient_id','initials','fecha_nacimiento']}, identificacion='duplicate')
        pseudo.pk = None; pseudo.external_id_namespace = 'another'; pseudo.identificacion = 'another'
        pseudo.full_clean(); pseudo.save()
        self.assertEqual(Paciente.objects.filter(initials='ACL').count(),2)
        pseudo.initials = ' '
        with self.assertRaises(ValidationError):pseudo.clean()

    def test_excel_exact_matching_and_birth_dates(self):
        self.assertNotEqual(patient_key('ACL'),patient_key('ACL2'))
        self.assertEqual(patient_key(' acl '),patient_key('ACL'))
        rows=read_patients(self.excel)
        self.assertEqual(rows['acl'][0].external_id,'007')
        xlsx(self.excel, [[7,'ACL','ignored',36526]], adapter='ijc1')
        row=read_patients(self.excel,'ijc1')['acl'][0]
        self.assertEqual(row.external_id,'7'); self.assertEqual(row.birth_date,date(2000,1,1))
        self.assertEqual(birth_date('1','n'),date(1900,1,1))
        self.assertEqual(birth_date('0','n',True),date(1904,1,1))
        for value, code in [('', 'MISSING_BIRTH_DATE'),('bad','INVALID_BIRTH_DATE'),('2999-01-01','INVALID_BIRTH_DATE')]:
            with self.assertRaises(ImportProblem) as ctx:birth_date(value,'s')
            self.assertEqual(ctx.exception.code,code)
        with self.assertRaises(ImportProblem):birth_date('60','n')

    def test_patient_missing_ambiguous_and_data_conflict(self):
        xlsx(self.excel,[['ACL2','8','ACL2','2000-01-01']])
        self.assertEqual(self.run_import(dry_run=True)['rows'][0]['status'],'PATIENT_NOT_FOUND')
        xlsx(self.excel,[['ACL','7','ACL','2000-01-01'],[' acl ','8','ACL','2000-01-01']])
        self.assertEqual(self.run_import(dry_run=True)['rows'][0]['status'],'PATIENT_MATCH_AMBIGUOUS')
        xlsx(self.excel)
        self.imported()
        xlsx(self.excel,[['ACL','007','ACL','2001-01-01']])
        self.assertEqual(self.run_import()['rows'][0]['status'],'PATIENT_DATA_CONFLICT')

    def test_mask_all_optional_class_combinations(self):
        for values in [[],[255],[85],[170],[85,255],[170,255],[170,85],[170,85,255]]:
            with self.subTest(values=values):
                a=np.zeros((40,40),dtype='uint8')
                for i,value in enumerate(values):a[2:7,2+i*10:7+i*10]=value
                Image.fromarray(a).save(self.mask)
                _, normalized,_=convert_pair(self.image,self.mask)
                self.assertEqual(len(normalized['objects']),len(values))
                self.assertEqual(len({o['id'] for o in normalized['objects']}),len(values))
                self.assertTrue(all(o['provenance']['origin']=='manual' for o in normalized['objects']))
        a[0,0]=1; Image.fromarray(a).save(self.mask)
        with self.assertRaises(ImportProblem) as ctx:convert_pair(self.image,self.mask)
        self.assertEqual(ctx.exception.code,'UNEXPECTED_MASK_VALUE')

    def test_cell_region_occlusions_and_real_holes(self):
        for value in (255,85):
            a=np.zeros((40,40),dtype='uint8');a[2:35,2:35]=170;a[10:18,10:18]=value
            Image.fromarray(a).save(self.mask)
            _,n,_=convert_pair(self.image,self.mask)
            self.assertEqual(n['summary']['counts_by_label']['membrana'],1)
            self.assertEqual(len(n['objects']),2)
        a[10:18,10:18]=0;Image.fromarray(a).save(self.mask)
        with self.assertRaises(ImportProblem) as ctx:convert_pair(self.image,self.mask)
        self.assertEqual(ctx.exception.detail,'REAL_HOLE')

    def test_topology_general_rules(self):
        for shape, reason in [('hole','REAL_HOLE'),('diagonal','DIAGONAL_BRIDGE'),('pixel','DEGENERATE_CONTOUR')]:
            a=np.zeros((40,40),dtype='uint8')
            if shape=='hole':a[2:20,2:20]=255;a[6:9,6:9]=0
            elif shape=='diagonal':a[2:7,2:7]=255;a[7:12,7:12]=255
            else:a[3,3]=255
            Image.fromarray(a).save(self.mask)
            report=self.run_import(dry_run=True)
            self.assertEqual(report['rows'][0]['status'],'UNSUPPORTED_POLYGON_TOPOLOGY')
            self.assertEqual(report['rows'][0]['detail'],reason)
            self.assertEqual(Paciente.objects.count(),0)
        with self.assertRaises(ImportProblem) as ctx:validate_contour([[1,1],[9,9],[1,9],[9,1]],10,10)
        self.assertEqual(ctx.exception.detail,'SELF_INTERSECTION')
        a=np.zeros((40,40),dtype='uint8');a[0:6,0:6]=85;Image.fromarray(a).save(self.mask)
        self.assertEqual(self.run_import(dry_run=True)['errors'],0)

    def test_pairing_formats_and_dimensions(self):
        Image.new('L',(10,10)).save(self.mask)
        self.assertEqual(self.run_import(dry_run=True)['rows'][0]['status'],'DIMENSION_MISMATCH')
        self.mask.unlink()
        self.assertEqual(self.run_import(dry_run=True)['rows'][0]['status'],'IMAGE_WITHOUT_MASK')
        Image.fromarray(self.pixels).save(self.mask)
        self.image.unlink()
        self.assertEqual(self.run_import(dry_run=True)['rows'][0]['status'],'MASK_WITHOUT_IMAGE')
        Image.new('RGB',(40,40)).save(self.image)
        Image.new('RGB',(40,40)).save(self.folder/'sample.jpg')
        self.assertEqual(self.run_import(dry_run=True)['rows'][0]['status'],'AMBIGUOUS_PAIR')

    def test_dry_run_has_zero_writes(self):
        with patch('api.services.imagej.importer.save_copy', side_effect=AssertionError('storage write')):
            report=self.run_import(dry_run=True)
        self.assertEqual(report['ready'],1)
        self.assertEqual(report['counts'],{'membrana':0,'nucleo':1,'micronucleo':1})
        for model in [Paciente,Caso,AnalisisPred,MuestraSaliva,ResultadoSegmentacion,RevisionSegmentacion,ImageJImportRecord]:self.assertEqual(model.objects.count(),0)
        self.assertFalse(self.media.exists())

    def test_import_domain_storage_and_no_science(self):
        with patch('api.views.segment_image',side_effect=AssertionError('segmentation')),patch('api.services.characterization.service.get_or_create_resultado_caracterizacion',side_effect=AssertionError('characterization')):
            record=self.imported()
        self.assertEqual(record.paciente.external_patient_id,'007')
        self.assertNotEqual(str(record.paciente.pk),'007')
        self.assertEqual(record.caso.case_number,1)
        self.assertEqual(record.muestra.analisis.id_paciente_fk_id,record.paciente_id)
        self.assertEqual(record.resultado.base_origin,'MANUAL')
        self.assertIsNone(record.resultado.segmentation_strategy)
        self.assertEqual(RevisionSegmentacion.objects.count(),0)
        self.assertEqual(ResultadoCaracterizacion.objects.count(),0)
        self.assertEqual(sha256_path(Path(record.source_mask_file.path)),sha256_path(self.mask))
        self.assertEqual(sha256_path(Path(record.muestra.imagen.path)),sha256_path(self.image))
        self.assertEqual(len(self.files()),2)

    def test_identical_reimport_noop_with_draft_and_validated(self):
        record=self.imported(); before=self.files(); payload=copy.deepcopy(record.resultado.resultado_normalizado)
        url=f'/api/resultados-segmentacion/{record.resultado_id}/revisiones/'
        draft=self.client.post(url,{},format='json').json()
        for validate in (False,True):
            if validate:self.client.post(f"/api/revisiones-segmentacion/{draft['id_revision_segmentacion']}/validar/",{},format='json')
            self.assertEqual(self.run_import()['rows'][0]['status'],'ALREADY_IMPORTED')
            self.assertEqual(self.files(),before)
            self.assertEqual(ImageJImportRecord.objects.count(),1)
            self.assertEqual(RevisionSegmentacion.objects.count(),1)
        record.resultado.refresh_from_db();self.assertEqual(record.resultado.resultado_normalizado,payload)

    def test_changed_files_and_version_never_overwrite(self):
        record=self.imported(); initial=list(self.files())
        self.pixels[25:30,25:30]=85;Image.fromarray(self.pixels).save(self.mask)
        self.assertEqual(self.run_import()['rows'][0]['status'],'MASK_CHANGED_CONFLICT')
        Image.new('RGB',(40,40),(2,3,4)).save(self.image)
        self.assertEqual(self.run_import()['rows'][0]['status'],'IMAGE_CHANGED_CONFLICT')
        self.assertEqual(self.files(),initial)
        self.assertEqual(ResultadoSegmentacion.objects.count(),1)
        with patch('api.services.imagej.importer.CONVERTER_VERSION','2.0'):
            # Restore original image/mask from storage, never edit an annotation.
            self.image.write_bytes(Path(record.muestra.imagen.path).read_bytes())
            self.mask.write_bytes(Path(record.source_mask_file.path).read_bytes())
            self.assertEqual(self.run_import()['rows'][0]['status'],'CONVERTER_VERSION_CONFLICT')

    def test_case_reuse_unique_and_legacy_ambiguity(self):
        record=self.imported()
        with self.assertRaises(IntegrityError), transaction.atomic():Caso.objects.create(paciente=record.paciente,titulo='duplicate',case_number=1)
        Caso.objects.create(paciente=record.paciente,titulo='legacy')
        Caso.objects.create(paciente=record.paciente,titulo='legacy2')
        Image.new('RGB',(40,40),(99,0,0)).save(self.folder/'other.png')
        Image.fromarray(self.pixels).save(self.folder/'other.tif')
        self.assertEqual(self.run_import()['errors'],0)
        self.assertEqual(AnalisisPred.objects.count(),1)
        self.assertEqual(Caso.objects.filter(case_number=1).count(),1)
        record.caso.case_number=None;record.caso.save()
        Caso.objects.create(paciente=record.paciente,titulo='Caso 1')
        Image.new('RGB',(40,40),(23,24,25)).save(self.folder/'aaa.png')
        Image.fromarray(self.pixels).save(self.folder/'aaa.tif')
        self.assertEqual(self.run_import(dry_run=True,limit=1)['rows'][0]['status'],'CASE_AMBIGUOUS')

    def test_storage_rollback_keeps_preexisting_files(self):
        self.media.mkdir();sentinel=self.media/'existing.dat';sentinel.write_bytes(b'keep')
        with patch.object(ImageJImportRecord,'save',side_effect=IntegrityError('synthetic')):
            report=self.run_import()
        self.assertEqual(report['rows'][0]['status'],'DB_ERROR')
        self.assertEqual(self.files(),['existing.dat']);self.assertEqual(sentinel.read_bytes(),b'keep')
        for model in [Paciente,Caso,AnalisisPred,MuestraSaliva,ResultadoSegmentacion,ImageJImportRecord]:self.assertEqual(model.objects.count(),0)

    def test_manual_effective_editor_save_validate_and_characterization_guard(self):
        record=self.imported();result=record.resultado
        self.assertEqual(resolve_effective_segmentation(result)['fuente'],'MANUAL')
        rejected=self.client.post(f'/api/resultados-segmentacion/{result.pk}/caracterizar/',{},format='json')
        self.assertEqual(rejected.status_code,400)
        self.assertEqual(ResultadoCaracterizacion.objects.count(),0)
        draft_response=self.client.post(f'/api/resultados-segmentacion/{result.pk}/revisiones/',{},format='json')
        self.assertEqual(draft_response.status_code,201)
        draft=draft_response.json();snapshot=draft['resultado_editado']
        self.assertTrue(all(o['provenance']=={'origin':'manual','base_object_id':None} for o in snapshot['objects']))
        self.assertEqual(snapshot['objects'][0]['source'],result.resultado_normalizado['objects'][0]['source'])
        snapshot['objects'][0]['geometry']['points'][0]=[5,4]
        snapshot['objects'].append({'id':3,'label':'membrana','geometry':{'type':'polygon','points':[[1,1],[30,1],[30,30],[1,30]]},'provenance':{'origin':'manual','base_object_id':None}})
        url=f"/api/revisiones-segmentacion/{draft['id_revision_segmentacion']}/"
        self.assertEqual(self.client.patch(url,{'resultado_editado':snapshot},format='json').status_code,200)
        self.assertEqual(resolve_effective_segmentation(result)['fuente'],'MANUAL')
        self.assertEqual(self.client.post(url+'validar/',{},format='json').status_code,200)
        self.assertEqual(resolve_effective_segmentation(result)['fuente'],'VALIDADA')
        self.assertEqual(self.client.patch(url,{'resultado_editado':snapshot},format='json').status_code,409)

    def test_cli_privacy_limit_strict_and_errors(self):
        out=StringIO();call_command('import_imagej_dataset',**self.options,dry_run=True,limit=1,patient=[' acl '],stdout=out)
        self.assertIn('WOULD_IMPORT',out.getvalue());self.assertNotIn('2000-01-01',out.getvalue());self.assertNotIn('ACL',out.getvalue())
        self.mask.unlink()
        with self.assertRaises(CommandError):call_command('import_imagej_dataset',**self.options,dry_run=True,stdout=StringIO())
        self.assertEqual(Paciente.objects.count(),0)

    def test_multiple_exteriors_and_degenerate_polygon(self):
        a=np.zeros((20,20),dtype='uint8');a[2:5,2:5]=1;a[12:15,12:15]=1
        with self.assertRaises(ImportProblem) as ctx:component_polygon(a,a*255,255)
        self.assertEqual(ctx.exception.detail,'MULTIPLE_EXTERIORS')
        with self.assertRaises(ImportProblem):validate_contour([[1,1],[2,2],[3,3]],20,20)

    def test_synthetic_import_empty_or_only_one_class(self):
        for value in (0,85,170,255):
            with self.subTest(value=value):
                Image.new('RGB',(40,40),(value,3,4)).save(self.image)
                a=np.zeros((40,40),dtype='uint8');a[3:9,3:9]=value;Image.fromarray(a).save(self.mask)
                report=self.run_import(dataset_key=f'synthetic-{value}')
                self.assertEqual(report['errors'],0,report)
        self.assertEqual(ImageJImportRecord.objects.count(),4)
        self.assertEqual(Paciente.objects.count(),1)
        self.assertEqual(Caso.objects.count(),1)
        self.assertEqual(AnalisisPred.objects.count(),1)
        self.assertEqual(RevisionSegmentacion.objects.count(),0)

    def test_existing_case_adoption_and_patient_reuse_dry_run(self):
        from api.services.imagej.importer import resolve_domain
        row=read_patients(self.excel)['acl'][0]
        p,_,_=resolve_domain(row,'test');p.save()
        case=Caso.objects.create(paciente=p,titulo='Caso 1')
        report=self.run_import(dry_run=True)
        self.assertEqual(report['cases_would_reuse'],1)
        case.refresh_from_db();self.assertIsNone(case.case_number)
        record=self.imported()
        self.assertEqual(record.caso_id,case.pk)
        self.assertEqual(record.caso.case_number,1)

    def test_partial_storage_failure_cleans_only_owned_files(self):
        from django.core.files.storage import default_storage
        original=default_storage.save
        def broken(name, content, **kwargs):
            original(name,content,**kwargs)
            raise OSError('simulated partial write')
        with patch.object(default_storage,'save',side_effect=broken):report=self.run_import()
        self.assertEqual(report['rows'][0]['status'],'STORAGE_ERROR')
        self.assertEqual(self.files(),[])
        self.assertEqual(Paciente.objects.count(),0)

    def test_legacy_layouts_duplicate_id_and_precision(self):
        _,pairs=discover(self.dataset/'pacientes','legacy-flat')
        self.assertEqual(len(pairs),1)
        nested=self.folder/'ACL';nested.mkdir()
        self.image.rename(nested/self.image.name);self.mask.rename(nested/self.mask.name)
        _,pairs=discover(self.dataset/'pacientes','legacy-repeated')
        self.assertEqual(len(pairs),1)
        xlsx(self.excel,[['ACL','7','ACL','2000-01-01'],['XYZ','7','XYZ','2000-01-01']])
        with self.assertRaises(ImportProblem) as ctx:read_patients(self.excel)
        self.assertEqual(ctx.exception.code,'DUPLICATE_PATIENT_ID')
        xlsx(self.excel,[['ACL',1234567890123456,'ACL','2000-01-01']])
        with self.assertRaises(ImportProblem) as ctx:read_patients(self.excel)
        self.assertEqual(ctx.exception.code,'INVALID_PATIENT_ID')

    def test_strict_stops_while_default_continues(self):
        (self.folder/'a.tif').write_bytes(self.mask.read_bytes())
        report=self.run_import(dry_run=True)
        self.assertEqual(report['errors'],1);self.assertEqual(report['ready'],1)
        report=self.run_import(dry_run=True,strict=True)
        self.assertEqual(report['errors'],1);self.assertEqual(report['ready'],0)

    def test_noop_does_not_reopen_closed_analysis(self):
        record=self.imported()
        analysis=record.muestra.analisis;analysis.estado=2;analysis.save()
        self.assertEqual(self.run_import()['rows'][0]['status'],'ALREADY_IMPORTED')
        analysis.refresh_from_db();self.assertEqual(analysis.estado,2)

    def test_late_source_changes_rollback_and_leave_no_domain(self):
        from api.services.imagej.importer import persist_pair
        original=persist_pair
        def changed(*args, **kwargs):
            self.mask.write_bytes(b'changed after preflight')
            return original(*args, **kwargs)
        with patch('api.services.imagej.importer.persist_pair', side_effect=changed):report=self.run_import()
        self.assertEqual(report['rows'][0]['status'],'SOURCE_CHANGED_DURING_IMPORT')
        self.assertEqual(Paciente.objects.count(),0);self.assertEqual(self.files(),[])

    def test_case_serializer_reports_duplicate_instead_of_database_error(self):
        record=self.imported()
        response=self.client.post('/api/casos/', {'paciente':record.paciente_id, 'titulo':'Duplicate', 'case_number':1}, format='json')
        self.assertEqual(response.status_code,400)
        self.assertEqual(Caso.objects.count(),1)

    def test_old_columns_compatible_with_null_case_numbers_and_automatic_origin(self):
        patient=Paciente.objects.create(nombre='Synthetic',apellido='Legacy',fecha_nacimiento=date(2000,1,1),identificacion='legacy-fields')
        self.assertEqual(patient.identity_mode,'IDENTIFIED')
        self.assertEqual(patient.external_id_namespace,'')
        case=Caso.objects.create(paciente=patient,titulo='Old case')
        self.assertIsNone(case.case_number)
        analysis=AnalisisPred.objects.create(id_paciente_fk=patient,id_caso_fk=case)
        sample=MuestraSaliva.objects.create(analisis=analysis,imagen='test-not-read.png')
        result=ResultadoSegmentacion.objects.create(muestra=sample,respuesta_json={},resultado_normalizado={'objects':[]})
        self.assertEqual(result.base_origin,'AUTOMATIC')
        self.assertEqual(resolve_effective_segmentation(result)['fuente'],'AUTOMATICO')
