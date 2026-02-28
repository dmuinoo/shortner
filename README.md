🔗 Short – Acortador de URLs Seguro y Preparado para Producción










Acortador de URLs desarrollado con FastAPI + SQLAlchemy, diseñado con foco en:

🔐 Seguridad avanzada

⚡ Eficiencia

🧱 Resiliencia

🏗️ Escalabilidad

🔁 Reproducibilidad

No es un shortener básico de demostración. Está diseñado con mentalidad de producción.

🚀 Características Principales
🔹 Acortamiento de URLs

Generación automática de short_code

Soporte para custom_key

Prevención de colisiones (retry + constraint DB)

secret_key único por URL para administración

Contador de clics

🔹 Administración por Capability

Cada URL genera un secret_key único.

Quien posee ese secret_key puede administrar la URL.

Endpoints administrativos
GET     /admin/{secret_key}
GET     /admin/{secret_key}/validate
POST    /admin/{secret_key}/enable
POST    /admin/{secret_key}/disable
PATCH   /admin/{secret_key}/expiry
DELETE  /admin/{secret_key}

Modelo: Capability-based security

No requiere autenticación.

🔄 Ciclo de Vida de la URL

Estados posibles:

active

disabled

expired

Caducidad configurable
PATCH /admin/{secret_key}/expiry
{
  "expires_in_days": 30
}

Comportamiento:

Disabled → HTTP 410

Expired → HTTP 410

Active → Redirect 307

🛡️ Seguridad
1️⃣ Validación fuerte de target_url

Solo http y https

Host obligatorio

Sin credenciales en URL

Longitud máxima configurable

Rechazo de espacios

Bloqueo de:

localhost

loopback

IPs privadas

IPs reservadas

Normalización punycode (IDNA)

Validación DNS opcional

2️⃣ Protección avanzada contra SSRF

Mitiga:

SSRF clásico

DNS rebinding

Dominios públicos que resuelven a red interna

Bypass mediante CNAME

IP literal privada

Mecanismo

Si resolve_dns=True:

Se resuelve el dominio.

Se validan todas las IPs devueltas.

Se bloquea si alguna IP es privada o reservada.

3️⃣ No actúa como proxy

El sistema NO realiza HEAD/GET al destino.

La redirección es puramente:

Location: <target_url>

Ventajas:

No puede ser abusado como proxy

No ejecuta SSRF activo

Latencia mínima

No depende del servidor destino

4️⃣ Motor de Políticas (Allowlist / Denylist)

Listas independientes:

app_allowlist.txt

app_denylist.txt

target_allowlist.txt

target_denylist.txt

Soportan:

IP

CIDR

Dominio

Wildcard (*.example.com)

FQDN

URL completa

Modo configurable:

default_app_policy = "allow" | "deny"
default_target_policy = "allow" | "deny"
⚡ Eficiencia
Caché DNS inteligente

Modos disponibles:

TTL fijo
dns_cache_mode = "fixed"
dns_cache_ttl_seconds = 300
TTL real DNS
dns_cache_mode = "dns"

Incluye clamp mínimo/máximo.

Soporte Redis (opcional)

Permite:

Caché compartida

Escalabilidad horizontal

Preparación para rate limiting distribuido

Ruta de redirección optimizada

Flujo:

Lookup DB

Validación de estado

Validación DNS cacheada

RedirectResponse

Sin llamadas externas.

🧱 Resiliencia
Prevención de colisiones

Constraint único

Retry hasta 20 intentos

Evolución ligera de esquema SQLite
ensure_sqlite_schema(engine)
Degradación controlada

Si Redis falla:

Se usa caché local

Servicio sigue operativo

📊 Observabilidad

Logging estructurado JSON:

{
  "event": "redirect",
  "ip": "...",
  "ua": "...",
  "key": "abc123"
}

Compatible con:

ELK

Loki

SIEM

🌍 Geolocalización (Preparado)

Infraestructura implementada:

Resolución IP → country_code

Caché GeoIP con TTL

Feature toggle disponible

Estado actual:

🚧 Implementado a nivel de infraestructura
❌ No activado aún como política en producción

🏗️ Arquitectura
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

Diseñado para alta disponibilidad.

🔁 Reproducibilidad

Se usa:

pyproject.toml

uv.lock

Generar lock:

uv lock

Instalar exactamente lo bloqueado:

uv sync --frozen
📌 Estado Actual

Implementado:

Acortamiento

Custom keys

Caducidad

Enable / Disable

Administración por capability

Protección SSRF

Motor de políticas

Caché DNS

Logging estructurado

Preparado:

GeoIP enforcement por país

Rate limiting distribuido

Multi-tenant

🔮 Roadmap

JWT / API Keys

Multi-tenant real

Estadísticas avanzadas

Panel web

Alembic

Alta disponibilidad activa-activa

📐 DIAGRAMA DE SEGURIDAD
[Input URL]
    ↓
Validación sintáctica
    ↓
Normalización punycode
    ↓
Policy Engine (allow/deny)
    ↓
DNS Resolve (opcional)
    ↓
Validación IP resultante
    ↓
Persistencia
📘 Whitepaper Técnico (Resumen)

Este sistema aplica principios de:

Defense in Depth

Capability-based access control

Fail-safe defaults

Secure by design

Stateless architecture

Horizontal scalability readiness

La mitigación SSRF incluye validación a nivel:

Sintáctico

Dominio

IP literal

Resolución DNS

Política configurable

Caché optimizada

Si quieres ahora puedo generarte:

🧪 Plan de testing profesional

🧱 Documento técnico de arquitectura formal

📊 Documento de análisis de riesgos

🧾 Licencia MIT preparada

🧑‍💻 Contributing.md

Dime qué quieres añadir al repo para dejarlo nivel senior.
