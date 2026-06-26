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

# Modelo de Máscara
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