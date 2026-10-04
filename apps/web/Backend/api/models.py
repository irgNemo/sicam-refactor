import uuid

from django.core.exceptions import ValidationError
from django.db import models
from .segmentation_strategies import SalivaSegmentationStrategy

# Modelo de Paciente
class Paciente(models.Model):
    IDENTIFIED = 'IDENTIFIED'
    PSEUDONYMIZED = 'PSEUDONYMIZED'
    id_paciente = models.AutoField(primary_key=True)
    identity_mode = models.CharField(
        max_length=20,
        choices=[(IDENTIFIED, 'Identificado'), (PSEUDONYMIZED, 'Pseudonimizado')],
        default=IDENTIFIED,
    )
    external_id_namespace = models.CharField(max_length=64, blank=True, default='')
    external_patient_id = models.CharField(max_length=100, blank=True, default='')
    initials = models.CharField(max_length=100, blank=True, default='')
    nombre = models.CharField(max_length=100, blank=True, default='')
    apellido = models.CharField(max_length=100, blank=True, default='')
    fecha_nacimiento = models.DateField()
    identificacion = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['external_id_namespace', 'external_patient_id'],
                condition=~models.Q(external_id_namespace=''),
                name='patient_external_identity_unique',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(external_id_namespace='', external_patient_id='') |
                    (~models.Q(external_id_namespace='') & ~models.Q(external_patient_id=''))
                ),
                name='patient_external_identity_complete',
            ),
            models.CheckConstraint(
                check=(
                    (models.Q(identity_mode='IDENTIFIED') & ~models.Q(nombre='') & ~models.Q(apellido='')) |
                    (models.Q(identity_mode='PSEUDONYMIZED', nombre='', apellido='') &
                     ~models.Q(initials='') & ~models.Q(external_id_namespace='') &
                     ~models.Q(external_patient_id=''))
                ),
                name='patient_identity_mode_consistency',
            ),
        ]

    def clean(self):
        super().clean()
        if self.identity_mode == self.IDENTIFIED:
            if not (self.nombre or '').strip() or not (self.apellido or '').strip():
                raise ValidationError('Nombre y apellido son obligatorios para IDENTIFIED.')
        elif self.identity_mode == self.PSEUDONYMIZED:
            if self.nombre or self.apellido or not all((v or '').strip() for v in (self.initials, self.external_id_namespace, self.external_patient_id)):
                raise ValidationError('PSEUDONYMIZED requiere iniciales e identidad externa, sin nombre ni apellido.')
        else:
            raise ValidationError('identity_mode no válido.')
        if bool((self.external_id_namespace or '').strip()) != bool((self.external_patient_id or '').strip()):
            raise ValidationError('La identidad externa requiere namespace e ID.')

    @property
    def display_name(self):
        return self.initials if self.identity_mode == self.PSEUDONYMIZED else f'{self.nombre} {self.apellido}'.strip()

    def __str__(self):
        return f"{self.display_name} - {self.identificacion}"

# Modelo de Caso
class Caso(models.Model):
    id_caso = models.AutoField(primary_key=True)
    case_number = models.PositiveIntegerField(null=True, blank=True)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='casos'
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['paciente', 'case_number'],
                condition=models.Q(case_number__isnull=False),
                name='case_number_per_patient_unique',
            ),
            models.CheckConstraint(
                check=models.Q(case_number__isnull=True) | models.Q(case_number__gt=0),
                name='case_number_positive',
            ),
        ]
    
    def __str__(self):
        return f"Caso {self.id_caso} - {self.titulo}"

# Modelo de Análisis
class AnalisisPred(models.Model):
    ESTADO_CHOICES = [
        (0, 'Abierto'),
        (1, 'En Proceso'),
        (2, 'Cerrado'),
    ]

    id_analisis = models.AutoField(primary_key=True)
    id_paciente_fk = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='analisis'
    )
    id_caso_fk = models.ForeignKey(
        Caso,
        on_delete=models.CASCADE,
        related_name='analisis'
    )
    fecha = models.DateField(auto_now_add=True)
    estado = models.IntegerField(
        choices=ESTADO_CHOICES,
        default=0
    )
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Analisis {self.id_analisis} - {self.get_estado_display()}"

# Modelo de Muestra de Saliva
class MuestraSaliva(models.Model):
    id_muestra = models.AutoField(primary_key=True)
    analisis = models.ForeignKey(
        AnalisisPred,
        on_delete=models.CASCADE,
        related_name='muestras_saliva'
    )
    imagen = models.ImageField(
        upload_to='muestras/saliva/%Y/%m/'
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Muestra Saliva {self.id_muestra}"


# Modelo de Muestra de Sangre
class MuestraSangre(models.Model):
    id_muestra = models.AutoField(primary_key=True)
    analisis = models.ForeignKey(
        AnalisisPred,
        on_delete=models.CASCADE,
        related_name='muestras_sangre'
    )
    imagen = models.ImageField(
        upload_to='muestras/sangre/%Y/%m/'
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Muestra Sangre {self.id_muestra}"

# Modelo de Resultado
class ResultadoAnalisis(models.Model):
    id_resultado = models.AutoField(primary_key=True)
    muestra = models.ForeignKey(
        MuestraSaliva,
        on_delete=models.CASCADE,
        related_name='resultados'
    )
    nucleos = models.IntegerField()
    micronucleos = models.IntegerField()
    membranas = models.IntegerField()
    fecha_analisis = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resultado {self.id_resultado}"


# Modelo de resultado JSON de segmentacion
class ResultadoSegmentacion(models.Model):
    base_origin = models.CharField(
        max_length=12,
        choices=[('AUTOMATIC', 'Automático'), ('MANUAL', 'Manual')],
        default='AUTOMATIC',
    )
    id_resultado_segmentacion = models.AutoField(primary_key=True)
    muestra = models.ForeignKey(
        MuestraSaliva,
        on_delete=models.CASCADE,
        related_name='resultados_segmentacion',
        blank=True,
        null=True,
    )
    muestra_sangre = models.ForeignKey(
        MuestraSangre,
        on_delete=models.CASCADE,
        related_name='resultados_segmentacion',
        blank=True,
        null=True,
    )
    tipo_muestra = models.CharField(max_length=20, default='SALIVA')
    segmentation_strategy = models.CharField(
        max_length=40,
        choices=SalivaSegmentationStrategy.choices,
        null=True,
        blank=True,
    )
    respuesta_json = models.JSONField()
    resultado_normalizado = models.JSONField(blank=True, null=True)
    estado = models.CharField(max_length=20, default='COMPLETADO')
    error = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(base_origin='AUTOMATIC') | models.Q(
                    base_origin='MANUAL', tipo_muestra='SALIVA', segmentation_strategy__isnull=True,
                ),
                name='segmentation_base_origin_consistent',
            ),
            models.CheckConstraint(
                check=(
                    (
                        models.Q(tipo_muestra='SALIVA') &
                        models.Q(muestra__isnull=False) &
                        models.Q(muestra_sangre__isnull=True)
                    ) |
                    (
                        models.Q(tipo_muestra='SANGRE') &
                        models.Q(muestra__isnull=True) &
                        models.Q(muestra_sangre__isnull=False)
                    )
                ),
                name='resultado_segmentacion_sample_type_consistency',
            ),
        ]

    def __str__(self):
        return (
            f"Resultado Segmentacion {self.id_resultado_segmentacion} - "
            f"{self.tipo_muestra} - {self.estado}"
        )


# Modelo de Máscara
class RevisionSegmentacion(models.Model):
    ESTADO_BORRADOR = 'BORRADOR'
    ESTADO_VALIDADA = 'VALIDADA'
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_VALIDADA, 'Validada'),
    ]

    id_revision_segmentacion = models.AutoField(primary_key=True)
    resultado_segmentacion = models.ForeignKey(
        ResultadoSegmentacion,
        on_delete=models.CASCADE,
        related_name='revisiones'
    )
    numero_revision = models.PositiveIntegerField()
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_BORRADOR
    )
    resultado_editado = models.JSONField()
    resumen = models.JSONField()
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    validado_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['resultado_segmentacion', 'numero_revision'],
                name='unique_revision_per_resultado_segmentacion'
            ),
            models.UniqueConstraint(
                fields=['resultado_segmentacion'],
                condition=models.Q(estado='BORRADOR'),
                name='unique_active_draft_per_resultado_segmentacion'
            )
        ]
        ordering = ['numero_revision']

    def __str__(self):
        return (
            f"Revision Segmentacion {self.id_revision_segmentacion} - "
            f"Resultado {self.resultado_segmentacion_id} - "
            f"Revision {self.numero_revision} - {self.estado}"
        )


class ResultadoCaracterizacion(models.Model):
    SOURCE_AUTOMATICO = 'AUTOMATICO'
    SOURCE_VALIDADA = 'VALIDADA'
    SOURCE_CHOICES = [
        (SOURCE_AUTOMATICO, 'Automatico'),
        (SOURCE_VALIDADA, 'Validada'),
    ]

    id_resultado_caracterizacion = models.AutoField(primary_key=True)
    resultado_segmentacion = models.ForeignKey(
        ResultadoSegmentacion,
        on_delete=models.CASCADE,
        related_name='caracterizaciones',
    )
    revision_segmentacion = models.ForeignKey(
        RevisionSegmentacion,
        on_delete=models.PROTECT,
        related_name='caracterizaciones',
        blank=True,
        null=True,
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    sample_type = models.CharField(max_length=20)
    algorithm_version = models.CharField(max_length=20)
    resultado_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id_resultado_caracterizacion']
        constraints = [
            models.CheckConstraint(
                check=(
                    (
                        models.Q(source_type='AUTOMATICO') &
                        models.Q(revision_segmentacion__isnull=True)
                    ) |
                    (
                        models.Q(source_type='VALIDADA') &
                        models.Q(revision_segmentacion__isnull=False)
                    )
                ),
                name='resultado_caracterizacion_source_consistency',
            ),
        ]

    def __str__(self):
        return (
            f"Resultado Caracterizacion "
            f"{self.id_resultado_caracterizacion} - "
            f"Resultado {self.resultado_segmentacion_id} - "
            f"{self.source_type}"
        )

    def clean(self):
        super().clean()

        if self.source_type == self.SOURCE_AUTOMATICO:
            if self.revision_segmentacion_id is not None:
                raise ValidationError(
                    'Una caracterizacion AUTOMATICO no debe tener revision'
                )
            return

        if self.source_type == self.SOURCE_VALIDADA:
            if self.revision_segmentacion_id is None:
                raise ValidationError(
                    'Una caracterizacion VALIDADA requiere revision'
                )

            if (
                self.resultado_segmentacion_id is not None
                and self.revision_segmentacion.resultado_segmentacion_id
                != self.resultado_segmentacion_id
            ):
                raise ValidationError(
                    'La revision debe pertenecer al mismo resultado segmentacion'
                )

            if (
                self.revision_segmentacion.estado
                != RevisionSegmentacion.ESTADO_VALIDADA
            ):
                raise ValidationError(
                    'La revision asociada debe estar VALIDADA'
                )


class AnalisisMascara(models.Model):
    id_mascara_analisis = models.AutoField(primary_key=True)
    resultado = models.ForeignKey(
        ResultadoAnalisis,
        on_delete=models.CASCADE,
        related_name='mascaras'
    )
    tipo_mascara = models.CharField(max_length=50)
    imagen = models.ImageField(
        upload_to='mascaras/saliva/%Y/%m/'
    )
    algoritmo = models.CharField(max_length=100)
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mascara {self.tipo_mascara} - Resultado {self.resultado.id_resultado}"


class ImageJImportRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset_key = models.CharField(max_length=100)
    patient_namespace = models.CharField(max_length=64)
    external_patient_id = models.CharField(max_length=100)
    patient_key = models.CharField(max_length=100)
    case_number = models.PositiveIntegerField()
    logical_basename = models.CharField(max_length=255)
    image_sha256 = models.CharField(max_length=64)
    mask_sha256 = models.CharField(max_length=64)
    sample_key = models.CharField(max_length=64, unique=True)
    annotation_key = models.CharField(max_length=64, unique=True)
    logical_key = models.CharField(max_length=64, unique=True)
    converter_version = models.CharField(max_length=20)
    contract_version = models.CharField(max_length=40)
    source_mask_file = models.FileField(upload_to='imagej/source_masks/%Y/%m/', max_length=255)
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT)
    caso = models.ForeignKey(Caso, on_delete=models.PROTECT)
    muestra = models.OneToOneField(MuestraSaliva, on_delete=models.PROTECT)
    resultado = models.OneToOneField(ResultadoSegmentacion, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=[('READY', 'Ready')], default='READY')
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(case_number=1, status='READY') & ~models.Q(source_mask_file=''), name='imagej_record_ready')]
