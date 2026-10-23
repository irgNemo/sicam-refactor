import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.management.tenant import require_institution
from api.models import Paciente, AcquisitionProfile, AcquisitionSeries


class Command(BaseCommand):
    help = 'Asigna explícitamente TODOS los pacientes/perfiles legacy sin autoría ni cambios científicos.'

    def add_arguments(self, parser):
        parser.add_argument('--institution', required=True)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--confirm-all-unassigned', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        tenant = require_institution(options['institution'])
        patients = Paciente.objects.select_for_update().filter(institution__isnull=True)
        profiles = AcquisitionProfile.objects.select_for_update().filter(institution__isnull=True)
        patient_ids, profile_ids = list(patients.values_list('pk', flat=True)), list(profiles.values_list('pk', flat=True))
        # Check final ownership before touching either side of acquisition relationships.
        for series in AcquisitionSeries.objects.select_related('patient', 'acquisition_profile'):
            patient_tenant = tenant.pk if series.patient_id in patient_ids else series.patient.institution_id
            profile_tenant = tenant.pk if series.acquisition_profile_id in profile_ids else series.acquisition_profile.institution_id
            if patient_tenant != profile_tenant:
                raise CommandError('INSTITUTION_MISMATCH: resolver la serie antes de asignar.')
        for patient in patients:
            patient.institution = tenant
            try:
                patient.validate_constraints()
            except Exception:
                raise CommandError('PATIENT_IDENTITY_CONFLICT: no se asignó ownership.') from None
        self.stdout.write(json.dumps({'institution_id': tenant.pk, 'patient_ids': patient_ids,
                                     'profile_ids': profile_ids, 'dry_run': options['dry_run']}))
        if options['dry_run']:
            return
        if not options['confirm_all_unassigned']:
            raise CommandError('Revise --dry-run y use --confirm-all-unassigned explícitamente.')
        patients.update(institution=tenant)
        profiles.update(institution=tenant)
