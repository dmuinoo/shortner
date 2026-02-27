Aquí tienes el **README.md completo corregido**, alineado exactamente con los endpoints que aparecen en tu Swagger:

---

````markdown
# 🔗 Shortner — URL Shortener con FastAPI

Acortador de URLs desarrollado con **Python + FastAPI**, basado en el enfoque del curso de Real Python y extendido con endpoints administrativos y de consulta.

El servicio permite:

- Crear URLs cortas
- Redirigir automáticamente a la URL original
- Consultar información de una URL
- Administrar (ver info y eliminar) mediante `secret_key`

---

## 🚀 Stack tecnológico

- Python 3.10+
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite

---

## 📦 Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
````

---

## ▶️ Ejecución

```bash
uvicorn main:app --reload
```

Documentación interactiva disponible en:

* Swagger UI → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* OpenAPI JSON → [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

# 📡 Endpoints reales del proyecto

## 🔹 Short

### 1️⃣ GET `/`

Read Root

Endpoint básico de comprobación de servicio.

---

### 2️⃣ POST `/url`

Create URL

Crea una nueva URL acortada.

#### Request body (JSON)

```json
{
  "target_url": "https://example.com/muy/larga/url"
}
```

#### Response típica

```json
{
  "target_url": "https://example.com/muy/larga/url",
  "url_key": "abc123",
  "secret_key": "XyZ987secret"
}
```

* `url_key` → clave pública usada para redirección.
* `secret_key` → clave privada usada para administración.

---

### 3️⃣ GET `/{url_key}`

Forward To Target URL

Redirige automáticamente a la `target_url` asociada.

Ejemplo:

```
GET /abc123
```

→ Redirección HTTP 307 hacia la URL original.

---

## 🔹 Info

### 4️⃣ GET `/peek/{key}`

Peek URL

Permite consultar información pública de una URL acortada sin redirigir.

Ejemplo:

```
GET /peek/abc123
```

Devuelve metadata de la URL.

---

## 🔹 Admin

### 5️⃣ GET `/admin/{secret_key}`

Administration Info

Devuelve información administrativa asociada a una URL usando su `secret_key`.

Ejemplo:

```
GET /admin/XyZ987secret
```

---

### 6️⃣ DELETE `/admin/{secret_key}`

Delete URL

Elimina una URL acortada del sistema usando su `secret_key`.

Ejemplo:

```
DELETE /admin/XyZ987secret
```

---

# 🗃️ Modelo conceptual

Cada URL almacenada contiene:

* `target_url`
* `url_key` (clave pública)
* `secret_key` (clave privada administrativa)
* Metadatos adicionales (según implementación)

Separar `url_key` y `secret_key` permite:

* Redirección pública sin autenticación
* Administración segura sin sistema de usuarios

---

# 🛠️ Configuración

El proyecto puede utilizar variables de entorno para:

* Base URL del servicio
* Longitud del código
* Alfabeto permitido
* Base de datos

Ejemplo `.env`:

```
BASE_URL=http://127.0.0.1:8000
SHORT_CODE_LENGTH=6
```

---

# 🧭 Roadmap — Próximos Hitos

## ✅ H1 — Personalización del string generado

* Permitir configurar el alfabeto (`SHORT_CODE_ALPHABET`)
* Permitir definir longitud (`SHORT_CODE_LENGTH`)
* Estrategias de generación intercambiables:

  * Aleatoria
  * Determinista (hash)
  * Secuencial (base62 de ID)

---

## 🔁 H2 — Robustez ante colisiones

* Constraint UNIQUE en `url_key`
* Reintentos controlados
* Política para URLs duplicadas

---

## ✍️ H3 — Alias personalizado

* Permitir especificar manualmente `url_key`
* Lista de palabras reservadas

---

## ⏳ H4 — Expiración y estado

* Campo `expires_at`
* Estado activo/inactivo
* Soft delete

---

## 📊 H5 — Analítica básica

* Contador de visitas
* Timestamp último acceso
* Endpoint de estadísticas

---

## 🔐 H6 — Seguridad avanzada

* Rate limiting
* API keys
* Multiusuario

---

## 🧪 H7 — Calidad y despliegue

* Tests con pytest
* Dockerfile
* CI/CD
* Migraciones con Alembic

---

# 📜 Licencia

Añadir licencia (MIT recomendada).

---

# 📚 Créditos

Inspirado en el curso de Real Python:

[https://realpython.com/build-a-python-url-shortener-with-fastapi/](https://realpython.com/build-a-python-url-shortener-with-fastapi/)

---

