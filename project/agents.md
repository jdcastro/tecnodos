# Descripción general del proyecto

Guía operativa para agentes de código en el proyecto **TecnoAgro**. Resume arquitectura, convenciones, patrones y flujos para mantener y extender la aplicación con modularidad, seguridad, rendimiento y escalabilidad, aprovechando las funciones y herramientas integradas de Flask y las herramientas seleccionadas cumpliendo con PEP 8 y PEP 257.

---

## 🚀 Panorama General

- **Stack**:
  - Flask 3.1 (factory pattern)
  - SQLAlchemy + Flask-Migrate (ORM + migraciones)
  - JWT cookies con flask-jwt-extended (auth segura) 
  - Jinja2 + Tailwind CSS
  - Marshmallow (validación y serialización)
  - Redis (caching opcional vía Flask-Caching)

- **Dominios clave**:

  - Núcleo → `app/core` (auth, usuarios, roles, rbac).
  - Módulos verticales → `app/modules/*` (follaje, reportes, agrovista, media, etc.).
  - Helpers transversales → `app/helpers` (CRUD, validaciones, CSV, mailing, logging, route lister).
- **Patrones**: Blueprints (web/api), controladores con MethodView + RBAC, soft delete vía `active`, errores centralizados, plantillas temáticas (`app/templates/<theme>`).
- **Entrada**: `run.py` instancia vía `create_app()`, config desde `.env` validada por `Config.validate_config()`.

---

## 🏗️ Arquitectura y Carpetas

```
project/
 ├── app/
 │   ├── core/            # núcleo de autenticación, modelos base, controladores
 │   ├── helpers/         # utilidades transversales (CRUD, validators, CSV, mail)
 │   ├── modules/         # módulos verticales con blueprints web/api
 │   ├── static/          # assets (css, js, img)
 │   ├── templates/       # layouts, macros, parciales reutilizables
 │   ├── config.py        # configuración central
 │   ├── extensions.py    # inicialización de extensiones
 │   └── __init__.py      # factory create_app
 ├── migrations/          # migraciones de base de datos (Alembic)
 ├── run.py               # punto de entrada de la app
 ├── Makefile / scripts   # tareas de gestión
 └── requirements.txt     # dependencias
```

---

## 📦 Estructura del Módulo

Cada módulo está en:

```
project/app/modules/<nombre_modulo>/
```

Archivos y responsabilidades:

1. **`__init__.py`**

   - Registra los *blueprints* web (`/<modulo>`) y/o API (`/api/<modulo>`).
   - Importa `web_routes` y `api_routes`.

2. **`api_routes.py`**

   - Define endpoints REST JSON.
   - Solo enruta; delega lógica a `controller.py`.

3. **`web_routes.py`**

   - Define rutas que renderizan vistas Jinja2.
   - **Nota**: la UI consume datos de la API vía JS, no contiene lógica de negocio.

4. **`controller.py`**

   - Contiene la lógica de negocio del módulo.
   - Orquesta modelos, esquemas y helpers.

5. **`models.py`**

   - Define entidades ORM (SQLAlchemy).
   - Incluye `active` para soft delete.

6. **`schemas.py`**

   - Serialización y validación de datos (Marshmallow).
   - Separa input/output.

7. **`helpers.py`** *(opcional)*

   - Funciones auxiliares específicas del módulo.

8. **`templates/`**

   - Plantillas Jinja para vistas del módulo.
   - Extienden `app/templates/default/base.j2`.

---

## ⚙️ Responsabilidades por Capa

- **UI (web\_routes + templates)** → mostrar/consumir datos.
- **API (api\_routes)** → exponer servicios JSON.
- **Controller** → lógica de negocio central.
- **Models** → estructura DB.
- **Schemas** → validación/serialización.
- **Helpers** → utilidades comunes.
- **`__init__`** → registro de blueprints.

---

## 🎨 Plantillas Jinja2

- Tailwind + Flowbite.
- Heredan de `/app/templates/default/`.
- Usan macros para formularios, botones y headers.
- UI modular, ejemplo de `farms.j2`:

```jinja
{% extends "base.j2" %}
{% from "macros/_forms.j2" import render_input, render_select %}
{% set page_title = "Granjas" %}

{% block content %}
  <h1>{{ page_title }}</h1>
  <form method="get">
    {{ render_input('search', request.args.get('search'), 'Buscar granja') }}
  </form>
  <table>
    {% for farm in items %}
      <tr><td>{{ farm.name }}</td></tr>
    {% endfor %}
  </table>
{% endblock %}
```

---

## 🛡️ Guardrails

```python
def guardrails() -> dict[str, tuple[str, ...]]:
    return {
        "scalabilidad": (
            "Paginación en CRUDMixin.",
            "Usar joinedload/selectinload para evitar N+1.",
            "Jobs async para cargas pesadas.",
        ),
        "seguridad": (
            "JWT cookies seguras + CSRF.",
            "Validar siempre con Marshmallow/APIValidator.",
            "Aplicar multi-tenant scope en queries.",
        ),
        "rendimiento": (
            "Cachear catálogos con cache.memoize.",
            "Preload assets críticos en templates.",
        ),
        "operaciones": (
            "Migraciones limpias con Flask-Migrate.",
            "Documentar rutas con RouteLister.",
        ),
    }
```

---

## 🔄 Flujo de Trabajo

1. **Preparación**

   * Define si es un nuevo módulo/blueprint.
   * Diseña DB + migraciones.
   * Planea rutas y vistas.

2. **Desarrollo**

   * Usa estructura modular.
   * Implementa auth JWT + RBAC.
   * Optimiza queries y cache.

3. **Testing**

   * Unit (modelos, servicios).
   * Integración (endpoints, RBAC).
   * Seguridad (validaciones, CSRF).
   * Performance (payloads grandes).

---

## 📏 Lineamientos de Código

* PEP8 + PEP257, SOLID, DRY.
* Blueprints → modularidad.
* Input sanitizado contra SQLi/XSS/CSRF.
* Docstrings estilo OpenAPI.
* Logging estructurado (rotativo).
* Type hints en modelos, schemas y controladores.

---

## 📊 Observabilidad

* `app/helpers/error_handler.py` captura excepciones globales.
* JSON para `/api/*`, HTML para web.
* Logs rotativos, integrables con sistemas externos.

---

## 🎭 Theming y Assets

* `Config.THEME` selecciona carpeta de plantillas (`app/templates/<theme>`).
* UI consistente mediante macros/partials.
* Assets en `app/static/assets`.

---
