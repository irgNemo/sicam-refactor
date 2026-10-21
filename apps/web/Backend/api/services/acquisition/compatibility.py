"""Read original bytes and declared relations; never infer optics or rescale."""
import warnings

from PIL import Image, UnidentifiedImageError

from api.models import AcquisitionSeries, Calibration


def physical_compatibility(sample):
    result = {
        'compatible_for_physical_units': False,
        'status': None,
        'reasons': [],
        'acquisition_series_id': sample.acquisition_series_id,
        'calibration_id': None,
        'calibration_status': None,
        'profile': None,
        'source_dimensions': None,
    }

    def finish(status):
        result['status'] = status
        result['reasons'] = [] if result['compatible_for_physical_units'] else [status]
        return result

    if not sample.acquisition_series_id:
        return finish('NO_ACQUISITION_SERIES')
    # Read fresh metadata: retirement or patient changes must not use relation caches.
    series = AcquisitionSeries.objects.select_related('acquisition_profile', 'calibration').get(pk=sample.acquisition_series_id)
    profile, calibration = series.acquisition_profile, series.calibration
    result['profile'] = {
        'id': profile.pk, 'name': profile.name,
        'image_width_px': profile.image_width_px, 'image_height_px': profile.image_height_px,
        'image_mode': profile.image_mode,
    }
    from api.models import AnalisisPred
    patient_id = AnalisisPred.objects.values_list('id_paciente_fk_id', flat=True).get(pk=sample.analisis_id)
    if patient_id != series.patient_id:
        return finish('PATIENT_MISMATCH')
    if calibration is None:
        return finish('NO_CALIBRATION')
    result.update(calibration_id=calibration.pk, calibration_status=calibration.status)
    if calibration.acquisition_profile_id != profile.pk:
        return finish('PROFILE_MISMATCH')
    if calibration.status == Calibration.RETIRED:
        return finish('CALIBRATION_RETIRED')
    if calibration.status not in (Calibration.PROVISIONAL, Calibration.VALIDATED):
        return finish('INVALID_CALIBRATION')
    if (calibration.source_width_px, calibration.source_height_px) != (profile.image_width_px, profile.image_height_px):
        return finish('RESOLUTION_MISMATCH')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with sample.imagen.storage.open(sample.imagen.name, 'rb') as stream:
                with Image.open(stream) as image:
                    dimensions, mode = image.size, image.mode
                    image.verify()
            # Decode as well: header-only acceptance can miss truncated image data.
            with sample.imagen.storage.open(sample.imagen.name, 'rb') as stream:
                with Image.open(stream) as image:
                    image.load()
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        return finish('INVALID_IMAGE')
    result['source_dimensions'] = {'width': dimensions[0], 'height': dimensions[1]}
    if dimensions != (profile.image_width_px, profile.image_height_px):
        return finish('RESOLUTION_MISMATCH')
    if profile.image_mode and profile.image_mode != mode:
        return finish('IMAGE_MODE_MISMATCH')
    result.update(
        compatible_for_physical_units=True,
        scale_x_um_per_px=str(calibration.scale_x_um_per_px),
        scale_y_um_per_px=str(calibration.scale_y_um_per_px),
    )
    return finish('COMPATIBLE_PROVISIONAL' if calibration.status == Calibration.PROVISIONAL else 'COMPATIBLE')


def can_use_physical_units(sample):
    return physical_compatibility(sample)['compatible_for_physical_units']
