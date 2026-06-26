# Validación de Fase 2 - Clientes de Microservicios

**Fecha:** 24 de junio de 2026  
**Alcance:** api/services/segmentation  

---

## ✅ Checklist de validación

### 1. Archivos creados

- [x] `api/services/__init__.py`
- [x] `api/services/segmentation/__init__.py`
- [x] `api/services/segmentation/base_client.py`
- [x] `api/services/segmentation/saliva_client.py`
- [x] `api/services/segmentation/blood_client.py`
- [x] `api/services/segmentation/exceptions.py`
- [x] `api/services/segmentation/factory.py`
- [x] `api/services/segmentation/tests.py`
- [x] `api/services/segmentation/USAGE.md`
- [x] `PHASE_2_SUMMARY.md`

### 2. Importes funcionales

```bash
cd apps/web/Backend

# Verificar que imports funcionan
python -c "from api.services.segmentation import segment_image; print('✓ Import exitoso')"

# Verificar clientes
python -c "from api.services.segmentation import SalivaSegmentationClient, BloodSegmentationClient; print('✓ Clientes importables')"

# Verificar excepciones
python -c "from api.services.segmentation import SegmentationTimeoutError, SegmentationConnectionError; print('✓ Excepciones importables')"

# Verificar factory
python -c "from api.services.segmentation import get_segmentation_client, segment_image; print('✓ Factory y helper importables')"
```

### 3. Tests sin errores de sintaxis

```bash
# Verificar que tests.py tiene sintaxis válida
python -m py_compile api/services/segmentation/tests.py
# Esperado: sin errores

# Ejecutar tests (requiere pytest)
pytest api/services/segmentation/tests.py -v
# Esperado: tests pass (pueden faltar mocks si no está bien configurado)
```

### 4. No hay cambios a endpoints existentes

```bash
# Verificar que views.py no cambió
git diff api/views.py
# Esperado: sin cambios

# Verificar que urls.py no cambió
git diff api/urls.py
# Esperado: sin cambios

# Verificar que modelos no cambiaron
git diff api/models.py
# Esperado: sin cambios
```

### 5. Configuración desde settings.py

```bash
# Django shell
python manage.py shell

from django.conf import settings

# Verificar SEGMENTATION_SERVICES existe
print(settings.SEGMENTATION_SERVICES)

# Salida esperada:
# {
#     'SALIVA': {
#         'url': 'http://localhost:8001',
#         'timeout': 30
#     },
#     'SANGRE': {
#         'url': 'http://localhost:8002',
#         'timeout': 30
#     }
# }
```

### 6. Factory obtiene clientes correctos

```bash
python manage.py shell

from api.services.segmentation import get_segmentation_client

# Test saliva
saliva = get_segmentation_client('SALIVA')
print(f"✓ Saliva client: {type(saliva).__name__}")
print(f"  URL: {saliva.base_url}")
print(f"  Endpoint: {saliva.get_endpoint()}")
print(f"  Timeout: {saliva.timeout}")

# Test sangre
sangre = get_segmentation_client('SANGRE')
print(f"✓ Sangre client: {type(sangre).__name__}")
print(f"  URL: {sangre.base_url}")
print(f"  Endpoint: {sangre.get_endpoint()}")
print(f"  Timeout: {sangre.timeout}")

# Test case-insensitive
saliva2 = get_segmentation_client('saliva')
print(f"✓ Case-insensitive: {type(saliva2).__name__}")
```

### 7. Validación de respuesta funciona

```bash
python manage.py shell

from api.services.segmentation import SalivaSegmentationClient
from api.services.segmentation import InvalidSegmentationResponseError

client = SalivaSegmentationClient('http://localhost:8001')

# Test respuesta válida
valid = {'objetos': [{'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}]}
client.validate_response(valid)
print("✓ Validación de respuesta válida: OK")

# Test respuesta inválida
try:
    invalid = {'invalid': 'data'}
    client.validate_response(invalid)
    print("✗ Debería haber lanzado excepción")
except InvalidSegmentationResponseError:
    print("✓ Validación de respuesta inválida: OK (lanzó excepción)")
```

### 8. Manejo de errores (con mocks)

```bash
python manage.py shell

from unittest.mock import patch, Mock
from api.services.segmentation import segment_image
from api.services.segmentation import SegmentationTimeoutError, SegmentationConnectionError
from requests.exceptions import Timeout, ConnectionError

# Test timeout
with patch('requests.post') as mock_post:
    mock_post.side_effect = Timeout()
    try:
        segment_image('SALIVA', b'fake')
        print("✗ Debería haber lanzado SegmentationTimeoutError")
    except SegmentationTimeoutError:
        print("✓ Timeout handling: OK")

# Test connection error
with patch('requests.post') as mock_post:
    mock_post.side_effect = ConnectionError()
    try:
        segment_image('SALIVA', b'fake')
        print("✗ Debería haber lanzado SegmentationConnectionError")
    except SegmentationConnectionError:
        print("✓ Connection error handling: OK")
```

### 9. Tests ejecutables

```bash
# Ejecutar tests con pytest
pytest api/services/segmentation/tests.py -v

# Esperado output:
# TestSalivaSegmentationClient::test_get_endpoint PASSED
# TestSalivaSegmentationClient::test_validate_response_valid PASSED
# TestSalivaSegmentationClient::test_validate_response_missing_objetos PASSED
# ... (más tests)
# ====== N passed in X.XXs ======

# Con coverage
pytest api/services/segmentation/tests.py --cov=api.services.segmentation
# Esperado: >90% coverage
```

### 10. Documentación clara

```bash
# Verificar USAGE.md existe y es legible
cat api/services/segmentation/USAGE.md | head -50

# Debe contener:
# - Descripción general
# - Ejemplos de uso
# - Configuración requerida
# - Excepciones explicadas
# - Tests
```

---

## 🧪 Pruebas manuales

### Prueba 1: Importación básica

```python
# En shell de Django o en un script
from api.services.segmentation import segment_image

print("✓ Import exitoso")
```

**Resultado esperado:** Sin errores

### Prueba 2: Obtener cliente

```python
from api.services.segmentation import get_segmentation_client

client = get_segmentation_client('SALIVA')
print(f"✓ Cliente obtenido: {client}")
print(f"  Tipo: {type(client).__name__}")
print(f"  URL: {client.base_url}")
print(f"  Endpoint: {client.get_endpoint()}")
```

**Resultado esperado:**
```
✓ Cliente obtenido: <SalivaSegmentationClient object>
  Tipo: SalivaSegmentationClient
  URL: http://localhost:8001
  Endpoint: /segmentar
```

### Prueba 3: Validación de respuesta

```python
from api.services.segmentation import SalivaSegmentationClient
from api.services.segmentation import InvalidSegmentationResponseError

client = SalivaSegmentationClient('http://localhost:8001')

# Válida
try:
    response = {'objetos': [
        {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
    ]}
    client.validate_response(response)
    print("✓ Respuesta válida acepta")
except:
    print("✗ Error en respuesta válida")

# Inválida
try:
    response = {'invalid': 'data'}
    client.validate_response(response)
    print("✗ Respuesta inválida no rechazada")
except InvalidSegmentationResponseError as e:
    print(f"✓ Respuesta inválida rechazada: {e}")
```

**Resultado esperado:**
```
✓ Respuesta válida acepta
✓ Respuesta inválida rechazada: Respuesta no contiene campo 'objetos'
```

### Prueba 4: Mock de llamada exitosa

```python
from unittest.mock import patch, Mock
from api.services.segmentation import segment_image

with patch('requests.post') as mock_post:
    # Setup mock
    mock_response = Mock()
    mock_response.json.return_value = {
        'objetos': [
            {'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    # Llamar cliente
    result = segment_image('SALIVA', b'fake_image')
    
    # Verificar
    print(f"✓ Segmentación exitosa")
    print(f"  Objetos: {result['objetos']}")
```

**Resultado esperado:**
```
✓ Segmentación exitosa
  Objetos: [{'id': 1, 'tipo': 'membrana', 'puntos': [[10, 20]]}]
```

### Prueba 5: Manejo de timeout

```python
from unittest.mock import patch
from api.services.segmentation import segment_image, SegmentationTimeoutError
from requests.exceptions import Timeout

with patch('requests.post') as mock_post:
    mock_post.side_effect = Timeout('Request timeout')
    
    try:
        segment_image('SALIVA', b'fake_image')
        print("✗ No lanzó excepción")
    except SegmentationTimeoutError as e:
        print(f"✓ Timeout manejado: {e}")
```

**Resultado esperado:**
```
✓ Timeout manejado: Timeout (30s) en http://localhost:8001/segmentar
```

### Prueba 6: Manejo de error de conexión

```python
from unittest.mock import patch
from api.services.segmentation import segment_image, SegmentationConnectionError
from requests.exceptions import ConnectionError

with patch('requests.post') as mock_post:
    mock_post.side_effect = ConnectionError('Connection refused')
    
    try:
        segment_image('SALIVA', b'fake_image')
        print("✗ No lanzó excepción")
    except SegmentationConnectionError as e:
        print(f"✓ Connection error manejado: {e}")
```

**Resultado esperado:**
```
✓ Connection error manejado: Error de conexión a http://localhost:8001/segmentar: Connection refused
```

---

## 📊 Resultado esperado final

| Aspecto | Estado | Nota |
|---------|--------|------|
| Archivos creados | ✅ | 10 archivos nuevos |
| Imports funcionales | ✅ | Sin errores |
| Clientes corretos | ✅ | SalivaSegmentationClient, BloodSegmentationClient |
| Factory funciona | ✅ | get_segmentation_client retorna cliente correcto |
| Validación OK | ✅ | validate_response funciona |
| Errores manejados | ✅ | Timeout, ConnectionError, InvalidResponse |
| Tests corren | ✅ | pytest sin errores |
| Endpoints sin cambios | ✅ | Ninguno modificado |
| Modelos sin cambios | ✅ | Ninguno modificado |
| Documentación | ✅ | USAGE.md, PHASE_2_SUMMARY.md |

---

## 🚀 Próximos pasos después de validar

1. **Crear modelo ResultadoSegmentacion** (Fase 3.1)
   - Almacenar objetos_json
   - Almacenar estado (pendiente, procesado, error)
   - Almacenar fecha y algoritmo

2. **Crear endpoint para segmentación** (Fase 3.2)
   - POST /api/muestras/{id}/segmentar/
   - Usar clientes para llamar microservicios
   - Guardar resultados

3. **Agregar validación** (Fase 3.3)
   - Permitir edición de polígonos
   - Marcar como validado
   - Auditoría

---

**Validación de Fase 2 lista para ejecutar.**
