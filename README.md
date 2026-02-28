# 🔗 Short – Acortador de URLs Seguro y Preparado para Producción

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Production-green)
![Security](https://img.shields.io/badge/Security-SSRF%20Protected-critical)
![Status](https://img.shields.io/badge/Status-Active-success)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

Acortador de URLs desarrollado con **FastAPI + SQLAlchemy**, esta basado en el curso **"Shortener URL" de Real Python**, pero este se ha diseñado con foco en:

- 🔐 Seguridad avanzada  
- ⚡ Eficiencia  
- 🧱 Resiliencia  
- 🏗️ Escalabilidad  
- 🔁 Reproducibilidad  

Este proyecto no es un simple shortener de demostración. Está diseñado con mentalidad de producción.

---

# 🚀 Características Principales

## 🔹 Acortamiento de URLs

- Generación automática de `short_code`
- Soporte para `custom_key`
- Prevención de colisiones (constraint en base de datos + retry)
- `secret_key` único por URL para administración
- Contador de clics

---

## 🔹 Administración por Capability (sin autenticación)

Cada URL genera un `secret_key` único.

Quien posea ese `secret_key` puede administrar la URL.

### Endpoints administrativos

```
GET     /admin/{secret_key}
GET     /admin/{secret_key}/validate
POST    /admin/{secret_key}/enable
POST    /admin/{secret_key}/disable
PATCH   /admin/{secret_key}/expiry
DELETE  /admin/{secret_key}
```

Modelo utilizado: **Capability-based security**.

---

# 🔄 Ciclo de Vida de la URL

Estados posibles:

- `active`
- `disabled`
- `expired`

### Caducidad configurable

```json
PATCH /admin/{secret_key}/expiry
{
  "expires_in_days": 30
}
```

Comportamiento:

- Disabled → HTTP 410
- Expired → HTTP 410
- Active → Redirect 307

---

# 🛡️ Seguridad

La seguridad es un pilar fundamental del sistema.

---

## 1️⃣ Validación fuerte de `target_url`

Se valida tanto al crear la URL como (opcionalmente) antes de redirigir:

- Solo `http` y `https`
- Host obligatorio
- Sin credenciales (`user:pass@host`)
- Longitud máxima configurable
- Rechazo de espacios
- Bloqueo de:
  - `localhost`
  - `127.0.0.1`
  - `::1`
  - IPs privadas y reservadas
- Normalización punycode (IDNA)
- Resolución DNS opcional

---

## 2️⃣ Protección contra SSRF

El sistema mitiga:

- SSRF clásico
- DNS rebinding
- Dominios públicos que resuelven a redes internas
- Bypass mediante CNAME
- Uso directo de IP privada

### Funcionamiento

Si `resolve_dns=True`:

1. Se resuelve el dominio.
2. Se validan todas las IPs resultantes.
3. Si alguna IP pertenece a un rango privado/reservado → se bloquea.

---

## 3️⃣ Noaactua como proxy


El sistema **NO realiza HEAD/GET al destino**.

La redirección se realiza únicamente mediante:

```
Location: <target_url>
```

Ventajas:

- No puede ser abusado como proxy
- No ejecuta SSRF activo
- Latencia mínima
- No depende del estado del servidor destino

---

## 4️⃣ Motor de Políticas (Allowlist / Denylist)

Listas independientes:

- `app_allowlist.txt`
- `app_denylist.txt`
- `target_allowlist.txt`
- `target_denylist.txt`

Formatos soportados:

- IP
- CIDR
- Dominio
- FQDN
- Wildcards (`*.example.com`)
- URL completa (se extrae el host)

### Política configurable

```python
default_app_policy = "allow"  # o "deny"
default_target_policy = "allow"  # o "deny"
```

Permite cambiar de “permitir por defecto” a “bloquear por defecto” sin modificar el código.

---

# ⚡ Eficiencia

## 🔹 Caché DNS inteligente

Modos disponibles:

### TTL fijo

```python
dns_cache_mode = "fixed"
dns_cache_ttl_seconds = 300
```

### TTL real del DNS

```python
dns_cache_mode = "dns"
```

- Usa el TTL real del registro DNS
- Aplica límites mínimo y máximo
- Reduce re-resoluciones innecesarias
- Minimiza latencia en redirecciones

---

## 🔹 Soporte Redis (opcional)

Permite:

- Caché compartida entre múltiples instancias
- Preparación para rate limiting distribuido
- Escalabilidad horizontal

Si Redis no está disponible, el sistema degrada a caché en memoria.

---

## 🔹 Ruta de redirección optimizada

Flujo:

1. Consulta en base de datos
2. Validación de estado
3. (Opcional) validación DNS cacheada
4. RedirectResponse

No se realizan llamadas HTTP externas.

---

# 🧱 Resiliencia

## 🔹 Prevención de colisiones

- Constraint único en base de datos
- Reintento automático hasta 20 veces

---

## 🔹 Evolución ligera de esquema (SQLite)

```python
ensure_sqlite_schema(engine)
```

Permite añadir nuevas columnas sin romper instancias existentes.

---

## 🔹 Degradación controlada

Si Redis falla:

- Se usa caché local
- El servicio continúa operativo

---

# 📊 Observabilidad

Logging estructurado en JSON:

```json
{
  "event": "redirect",
  "ip": "...",
  "ua": "...",
  "key": "abc123"
}
```

Compatible con:

- ELK
- Loki
- SIEM
- Sistemas de logging centralizado

---

# 🌍 Geolocalización (Preparado)

Infraestructura implementada para integración con **MaxMind GeoLite2 Country**.

Incluye:

- Resolución IP → `country_code`
- Caché GeoIP con TTL configurable
- Feature toggle disponible

Estado actual:

- Infraestructura implementada  
- No activado aún como política en producción  

El archivo `.mmdb` se provisiona externamente y no se incluye en el repositorio.

---

# 🏗️ Arquitectura

```
Cliente
   ↓
Load Balancer (Nginx / HAProxy)
   ↓
FastAPI Instance 1
FastAPI Instance 2
   ↓
Redis (opcional)
   ↓
Base de datos
```

Diseñado para alta disponibilidad.

---

# 🔁 Reproducibilidad

Se utiliza:

- `pyproject.toml`
- `uv.lock`

Generar lockfile:

```
uv lock
```

Instalar exactamente las versiones bloqueadas:

```
uv sync --frozen
```

Garantiza reproducibilidad del entorno a largo plazo.

---

# 📌 Estado Actual

Implementado:

- Acortamiento de URLs
- Custom keys
- Caducidad configurable
- Activación / desactivación
- Administración por capability
- Protección SSRF
- Motor Allowlist / Denylist
- Caché DNS
- Logging estructurado

Preparado:

- Políticas por país (GeoIP enforcement)
- Rate limiting distribuido
- Multi-tenant

---

# 🔮 Roadmap

- JWT / API Keys
- Multi-tenant real
- Endpoint avanzado de estadísticas
- Panel web
- Migraciones con Alembic
- Alta disponibilidad activa-activa

---

# 📄 Licencia

MIT License
