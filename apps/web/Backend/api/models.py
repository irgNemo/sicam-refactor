from django.db import models

# Modelo de Paciente
class Paciente(models.Model):
    id_paciente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    identificacion = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.identificacion}"

# Modelo de Caso
class Caso(models.Model):
    id_caso = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='casos'
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
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
    id_resultado_segmentacion = models.AutoField(primary_key=True)
    muestra = models.ForeignKey(
        MuestraSaliva,
        on_delete=models.CASCADE,
        related_name='resultados_segmentacion'
    )
    tipo_muestra = models.CharField(max_length=20, default='SALIVA')
    respuesta_json = models.JSONField()
    resultado_normalizado = models.JSONField(blank=True, null=True)
    estado = models.CharField(max_length=20, default='COMPLETADO')
    error = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

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
