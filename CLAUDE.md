# Turon — API de trazabilidad

API de trazabilidad para el obrador de Fleca i Pastisseria Turon. Digitaliza
las 5 fichas internas de trazabilidad (ver
`Fitxes_Tracabilitat_Pastisseria_Turon_v2.docx` si está disponible en el
entorno de quien trabaje en este repo; si no, la especificación de abajo es
la fuente de verdad — es una digitalización fiel de esas fichas).

## Objetivo
1. Registrar entradas de materia prima, lotes en uso, semielaborados y producción diaria.
2. Vincular automáticamente cada elaboración con los lotes de materia prima abiertos en el momento de elaborarla.
3. Responder en segundos a dos preguntas: «con este lote de proveedor, qué se ha elaborado» (hacia delante) y «este producto, de qué lotes viene» (hacia atrás).

Los usuarios son el personal de obrador, desde una tablet. Registrar una línea tiene que ser rápido.

## Stack
- Python 3.12, FastAPI, SQLModel, Alembic, pytest + httpx, uv.
- SQLite (`data/turon.db`), sin usar nada específico de SQLite para poder migrar a PostgreSQL.
- Identificadores de dominio en catalán (como en las fichas). Comentarios y docstrings en castellano.
- Estructura: `app/{main.py, db.py, models/, schemas/, routers/, services/, seed.py}`, `tests/`, `alembic/`. La lógica de negocio va en `services/`, no en los routers.

## Modelo de datos
Todos los lotes (materia prima, semielaborado, producto) están en una sola tabla y se relacionan mediante un grafo de consumos.

- `ingredients`: id, nom, actiu. Seed: Farina, Sucre, Ou / ovoproducte, Mantega / greix, Llet / nata, Xocolata / cacau, Fruits secs, Gelatina / estabilitzant.
- `proveidors`: id, nom, actiu.
- `elaboracions`: id, nom, tipus (semielaborat|producte), prefix_lot, actiu.
  - Seed de semielaborados: Pa de pessic (PPE), Planxes (PLA), Yema (YEM), Crema (CRE), Trufa (TRU), Bany (BAN).
  - Seed de productos: Melindros (MEL), Magdalenes (MAG), Carquinyolis (CAR), Pastissos (PST), Braços (BRA), Mousses (MOU).
- `receptes`: qué ingredientes y qué semielaborados usa cada elaboración. Si una elaboración no tiene receta, se vinculan todos los lotes abiertos y la respuesta devuelve `recepta_incompleta = true`.
- `lots`: id, tipus (materia_primera|semielaborat|producte), codi, creat_at, responsable, observacions, anulat_per_id (nullable).
  - Materia prima (ficha 1): ingredient_id, proveidor_id, lot_proveidor, data_recepcio, caducitat, tipus_data (caducitat|consum_preferent). El codi es el lot_proveidor.
  - Semielaborado y producto (fichas 3 y 4): elaboracio_id, quantitat, unitat, elaborat_at, torn. El codi se genera.
- `consums`: lot_produit_id, lot_consumit_id, origen (automatic|manual). La PK es compuesta.
- `lots_en_us` (ficha 2): id, ingredient_id, lot_id, inici, fi (nullable), observacions. Índice único parcial para que solo haya un registro con `fi IS NULL` por ingrediente.
- `incidencies` (ficha 5): id, tipus (canvi_lot|devolucio|alerta|altra), data_hora, responsable, lot_afectat_id, lot_anterior_id, lot_nou_id, motiu, mesura_adoptada, comprovacio, comprovat_per, afectats_snapshot (JSON).

## Reglas de negocio
1. Al abrir un lote en uso, en la misma transacción se cierra el lote abierto del mismo ingrediente y se abre el nuevo. Si el lote está caducado, devuelve 422.
2. Al crear un semielaborado o un producto, para cada ingrediente de la receta se busca el lote abierto en `elaborat_at` (`inici <= elaborat_at AND (fi IS NULL OR fi > elaborat_at)`) y se crea el consumo con `origen = automatic`. Si algún ingrediente no tiene lote abierto, devuelve 409 indicando cuál.
3. Los consumos se pueden corregir a mano; los corregidos quedan con `origen = manual`.
4. Una elaboración puede consumir dos lotes del mismo ingrediente (cambio de lote a mitad de turno). En ese caso se crea automáticamente una incidencia `canvi_lot`.
5. Los códigos internos siguen el formato `PREFIX-DDMMAA-NN`, con NN secuencial por prefijo y día empezando en 01. El codi es único y la generación tiene que ser segura con concurrencia (reintentar si hay colisión).
6. Nunca se hace UPDATE ni DELETE sobre `lots` ni `consums`. Una corrección crea un lote nuevo y marca el anterior con `anulat_per_id`. Las consultas excluyen los anulados, salvo el historial.
7. Al crear una incidencia, `afectats_snapshot` guarda la trazabilidad hacia delante del lote afectado en ese momento.

## Trazabilidad
Se implementa con `WITH RECURSIVE` sobre `consums`, en dos direcciones:
- Hacia delante: todos los lotes que han consumido un lote dado, directa o indirectamente.
- Hacia atrás: todos los lotes consumidos hasta llegar a la materia prima.

La respuesta se agrupa por tipo e incluye codi, elaboración o ingrediente, fecha y cantidad.

## Endpoints
- `POST/GET /entrades` (filtros: ingredient_id, desde, fins, caduca_en_dies) — ficha 1
- `POST /lots-en-us`, `GET /lots-en-us`, `GET /lots-en-us/historial` — ficha 2
- `POST/GET /semielaborats` — ficha 3
- `POST/GET /productes` — ficha 4
- `POST/DELETE /lots/{id}/consums` (el DELETE anula, no borra); `POST /lots/{id}/anular`; `GET /lots/cerca?codi=`
- `GET /traca/endavant/{lot_id}`, `GET /traca/enrere/{lot_id}` — ficha 5
- `POST/GET /incidencies` — ficha 5
- `GET /informes/dia/{data}` en JSON y con `?format=pdf`
- CRUD de `/ingredients`, `/proveidors`, `/elaboracions`, `/receptes`

Sin autenticación en esta versión: `responsable` se recibe como texto.

## Tests obligatorios
- Abrir un lote cierra el anterior del mismo ingrediente.
- No puede haber dos lotes abiertos del mismo ingrediente.
- Un semielaborado creado a las 10:00 se vincula con el lote abierto a las 10:00, no con el que se abre a las 11:00.
- Devuelve 409 si falta un lote abierto para un ingrediente de la receta.
- Dos cremas del mismo día reciben los códigos CRE-140826-01 y CRE-140826-02.
- La trazabilidad hacia delante recorre tres niveles: farina → planxes → braços.
- La trazabilidad hacia atrás llega desde un producto hasta los lotes de proveedor.
- Una incidencia guarda el snapshot de afectados.
- Anular un lote no lo borra y lo excluye de las consultas.

## Fases
1. Modelos, migración inicial, seed, CRUD de catálogos, `/entrades`, `/lots-en-us` y sus tests.
2. Semielaborados y productos con vinculación automática y generación de códigos, con tests.
3. Trazabilidad e incidencias, con tests.
4. Informes en JSON y PDF.
5. Frontend para tablet (proyecto aparte).

No se pasa a la siguiente fase hasta que los tests de la actual estén en verde.

## Comandos
`uv run fastapi dev app/main.py` · `uv run pytest -q` · `uv run alembic upgrade head` · `uv run python -m app.seed`
