# 🔗 Shortner — URL Shortener con FastAPI

Acortador de URLs desarrollado con **Python + FastAPI**, inspirado en el enfoque de Real Python y extendido con endpoints de **consulta** y **administración** mediante `secret_key`.

## ✅ Qué hace

- **Crear URLs cortas** a partir de una URL objetivo
- **Redirigir** desde `/{url_key}` a la URL original
- **Persistir** enlaces en una base de datos SQLite ('shortener.db').
- Consultar información (enlaces creados) sin redirigir (`/peek/{key}`)
- Administrar una URL (info y borrado) usando `secret_key`

-- ACTUALIZACION 1 [H1 + H2 + H3]
- Comprueba que esa url esta activa antes de generar el string acortador
- Permite elegir el string acortador siempre que no se haya usado antes
- Comprueba que el string no es ninguna palabra reservada antes de asignarlo

-- ACTUALIZACION 2 [H4]
---

## 🧱 Stack

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite

---

## 📦 Requisitos

- Tener instalado **uv** (Astral) para gestionar dependencias y ejecución

---

## 🚀 Instalación (con `uv`)

> Este proyecto se instala y ejecuta con `uv`, no con `pip` ni activando venv manualmente.

1) Clona el repositorio:

```bash
git clone https://github.com/dmuinoo/shortner.git
cd shortner
````

2. Instala dependencias:

```bash
uv add
```

> Si tu repo ya tiene dependencias definidas (por ejemplo en `pyproject.toml` / `uv.lock`), `uv` las resolverá y preparará el entorno automáticamente.

---

## ▶️ Ejecutar en local

```bash
uv run uvicorn main:app --reload
```

Documentación interactiva:

* Swagger UI → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* OpenAPI JSON → [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

# 📡 Endpoints (URIs reales)

Según la documentación Swagger del proyecto:

## Short

### GET `/` — Read Root

Endpoint básico de comprobación.

---

### POST `/url` — Create Url

Crea una URL acortada.

**Body (JSON)**

```json
{
  "target_url": "https://example.com/muy/larga/url"
}
```

**Respuesta típica**

```json
{
  "target_url": "https://example.com/muy/larga/url",
  "url_key": "abc123",
  "secret_key": "XyZ987secret"
}
```

* `url_key`: clave pública usada para redirección
* `secret_key`: clave privada para administración

---

### GET `/{url_key}` — Forward To Target Url

Redirige a la URL original asociada a `url_key`.

Ejemplo:

```text
GET /abc123
```

→ Responde con redirección HTTP (302/307) hacia `target_url`.

---

## Info

### GET `/peek/{key}` — Peek Url

Devuelve información de la URL acortada **sin redirigir**.

Ejemplo:

```text
GET /peek/abc123
```

---

## Admin

### GET `/admin/{secret_key}` — Administration Info

Devuelve información administrativa de la URL asociada a `secret_key`.

Ejemplo:

```text
GET /admin/XyZ987secret
```

---

### DELETE `/admin/{secret_key}` — Delete Url

Elimina la URL acortada asociada a `secret_key`.

Ejemplo:

```text
DELETE /admin/XyZ987secret
```

---

## 🗃️ Modelo conceptual

Cada URL almacenada tiene dos claves:

* **`url_key`** (pública): sirve para redirección
* **`secret_key`** (privada): sirve para administración (ver/borrar)

Esto permite administrar enlaces sin necesidad (todavía) de un sistema de usuarios.

---

# 🧭 Roadmap — próximos hitos

## H1 — Personalización del string generado (alfabeto/longitudu) [REALIZADO]

* Configurar `SHORT_CODE_ALPHABET` (alfabeto permitido)
* Configurar `SHORT_CODE_LENGTH` (longitud del código)
* Estrategias de generación:

  * Aleatoria con control de colisiones
  * Determinista (hash + encoding)
  * Secuencial (ID → base62)

**Criterio de aceptación:** al cambiar alfabeto/longitud, cambian los códigos generados sin romper redirecciones existentes.

---

## H2 — Robustez ante colisiones y duplicados [REALIZADO]

* Constraint UNIQUE en `url_key`
* Reintentos acotados
* Política para URLs repetidas (idempotencia vs múltiples códigos)

---

## H3 — Alias personalizado [REALIZADO]

* Permitir que el cliente elija `url_key` (si está libre)
* Lista de palabras reservadas (`docs`, `admin`, etc.)

---

## H4 — Expiración y estado [REALIZADO]

* `expires_at`
* `is_active` / soft delete
* Validación avanzada de URL + denylist de dominios

---

## H5 — Analítica

* Contador de visitas
* Último acceso
* Endpoint de estadísticas

---

## H6 — Seguridad

* Rate limiting
* API keys/JWT (si se desea)
* Separación por usuario (multi-tenant)

---

## 🧪 Calidad

* Tests (pytest)
* CI (GitHub Actions)
* Dockerfile + despliegue

---

## Miggrgaciones

* Migracion con Alembic

---

## UI funcional basica

* Pagina simple con formulario de creacion (FastAPI + Jinja2 )
* Panel basico de administracion

---

## 📚 Créditos

Proyecto inspirado en el enfoque de Real Python para un URL shortener con FastAPI.

---

## 📜 Licencia

Pendiente de definir (MIT recomendada).

```
```

