# Sprint 17 — navegación e indexación parcial segura de Drive

## Resultado

Atlas conserva la actualización global de Drive y añade navegación estructural
y sincronización por carpeta, subárbol o archivo. El árbol ligero no contiene
texto, fragmentos ni embeddings y permanece físicamente separado del índice
documental.

## Arquitectura

### Índice estructural

`GoogleDriveStructureIndex` persiste únicamente `file_id`, nombre, MIME,
padre, raíz, ruta relativa, ancestros, fecha, tamaño e indicador de carpeta.
Su namespace se deriva de usuario, cuenta y raíz. Las carpetas técnicas
excluidas por el indexador documental se muestran como nodos, pero no se
recorren.

La caché en memoria usa:

- clave: hash de usuario + `drive_account_id` + `root_folder_id`;
- propietario: usuario y conexión de Drive;
- TTL: 120 segundos por defecto;
- invalidación: `force=True`, `invalidate()` o expiración;
- límite: 32 namespaces por instancia;
- errores: una lectura remota fallida no reemplaza el snapshot persistido;
- sensibilidad: solo metadatos estructurales, nunca contenido ni credenciales.

### Navegación

`DriveNavigationService` mantiene `current_folder_id` y breadcrumbs con la
clave completa `(user_id, session_id, drive_account_id, root_folder_id)`.
Soporta `/`, `.`, `..`, rutas desde `Atlas Project` y rutas relativas. `..` en
la raíz permanece en la raíz. La resolución compara nombres para recorrer,
pero la identidad y el estado se conservan siempre mediante IDs.

Si hay nombres duplicados no se elige arbitrariamente. La herramienta devuelve
candidatos y la conversación permite seleccionar un número; el ID se valida de
nuevo dentro del namespace autorizado antes de cambiar la ubicación.

Capacidades nuevas:

- `drive.structure.sync`
- `drive.pwd`
- `drive.cd`
- `drive.list`
- `drive.tree`
- `drive.resolve_path`
- `documents.index.sync_scope`

### Índice documental modular

`GoogleDriveDocumentIndex.sync()` conserva el contrato global. Internamente
delega en `sync_scope()` sin objetivo parcial, de modo que «Actualiza el índice
de Drive» sigue recorriendo la raíz completa.

`sync_scope()` acepta raíz, carpeta, recursividad o archivo. Una actualización
parcial comienza con el índice anterior y solo reemplaza o elimina entradas del
ámbito verificado. Si el listado parece truncado o Drive falla, no aplica
borrados inferidos.

Cada documento nuevo conserva procedencia de cuenta, propietario, raíz,
archivo, padre, ruta relativa, ancestros, carpeta de ámbito, revisión, hash de
contenido y versión del fragmentador. Los documentos del formato anterior se
leen sin migración destructiva y adquieren los campos nuevos cuando vuelven a
sincronizarse.

Los archivos vacíos se registran como estado derivado, sin contenido, para no
descargarlos indefinidamente mientras revisión, tamaño y fragmentador no
cambien.

### Renombrados, movimientos y eliminaciones

- Mismo `file_id`, revisión y tamaño: se actualizan nombre, padre y ruta sin
  descargar contenido.
- Contenido descargado con el mismo hash: el índice semántico reutiliza los
  vectores existentes.
- Movimiento observado por el árbol: se actualiza la procedencia aunque el
  archivo haya salido de la rama sincronizada.
- Eliminación: solo se retira dentro de un listado completo del ámbito.
- Error temporal o listado truncado: se conserva la entrada anterior.

### Recuperación por ámbito

La búsqueda léxica y semántica filtra antes de puntuar. RAG y
`KnowledgeRetriever` aceptan un ámbito opcional `global`, `root`, `subtree`,
`current` o `file`. El filtro conserva prioridades, procedencia, privacidad y
la recuperación híbrida; únicamente reduce el conjunto autorizado.

La sincronización semántica también acepta un ámbito. Los vectores de otras
ramas permanecen intactos y un cambio de metadatos no regenera embeddings.

## Conversación

Se reconocen de forma determinista, entre otras:

- «Ve a 04 - Python», «Entra en atlas_core», «Sube una carpeta».
- «Vuelve a Atlas Project», «Dónde estoy», «Muéstrame el árbol desde aquí».
- «Actualiza el índice de Drive» — siempre global.
- «Actualiza el índice de esta carpeta».
- «Actualiza el índice de 04 - Python y sus subcarpetas».
- «Actualiza solo semantic_index.py».
- «Busca OAuth solo en la carpeta actual» y «Busca OAuth en todo Drive».

Buscar o sincronizar no cambia la carpeta actual. Solo `drive.cd` modifica el
estado de navegación.

## Seguridad y compatibilidad

- OAuth continúa usando exclusivamente `drive.readonly`.
- La raíz sigue fijada a `Atlas Project`; el resolvedor no acepta una salida.
- Herramientas, estructura, resultados y navegación usan usuario, cuenta, raíz
  y sesión cuando corresponde.
- No se modificó `main.py`.
- Se conservan `self.tool_registry`, `self.tool_selector`,
  `self.framework_tool_registry`, `self.tool_manager` y
  `self.framework_tool_adapter`.
- No se fusionaron los sistemas de herramientas y no se hizo `git push`.

## Límites conocidos

- Atlas mantiene hoy una única conexión OAuth activa. Los namespaces ya están
  preparados para varias cuentas, pero el registro dinámico de una conexión
  distinta por usuario pertenece a un sprint futuro.
- Los documentos heredados sin propietario explícito se aceptan por
  compatibilidad. La siguiente sincronización los etiqueta; para aislamiento
  estricto inmediato tras actualizar, debe ejecutarse una sincronización
  global una vez como el usuario propietario.
- Drive no expone checksum para todos los documentos nativos. Si cambia la
  revisión remota se descarga el texto para calcular SHA-256; aun así, si el
  contenido es idéntico no se regeneran embeddings.
- No se provocaron renombrados ni movimientos reales porque el alcance es de
  solo lectura. Estos escenarios están cubiertos con dobles deterministas.
- No se añadieron tareas en segundo plano ni actualización automática al
  navegar. La política prudente queda preparada, pero continúa siendo
  explícita.

## Validación transversal de todas las ramas de Atlas Project

Validación real ejecutada el 19 de julio de 2026 con OAuth `drive.readonly`,
IDs reducidos a hashes de doce caracteres y sin conservar contenido.

Se resolvieron, navegaron y comprobaron `Atlas Project`, `01 - Raspberry`,
`02 - PC`, `04 - Python`, `11 - Backups` y `Releases`. También se validaron
una carpeta de segundo nivel, una carpeta profunda de nivel 5, una carpeta
vacía, una con documentos indexables, otra con cinco archivos no compatibles y
un archivo individual fuera de `00 - Documentación` y `04 - Python`. La mayor
profundidad real observada en el árbol fue 6.

No existe lógica productiva especial para `00`, `01`, `02`, `04` o `11`.
La auditoría sí encontró que `Releases` estaba en la lista técnica heredada;
se retiró porque era una exclusión injustificada por nombre. `Backup`,
`Backups`, `Releases` y cualquier carpeta numerada normal usan ahora exactamente
el mismo recorrido por IDs y relaciones parentales.

### Política exacta de exclusiones

Carpetas excluidas por nombre exacto, sin distinguir mayúsculas:

```text
.git
.agents
.pytest_cache
__pycache__
.mypy_cache
.ruff_cache
.venv
venv
node_modules
logs
```

El conjunto es configurable en los constructores del árbol y del índice. El
nodo excluido continúa visible con `traversal_status=excluded_by_policy` y
`exclusion_reason=technical_folder_name`, pero no se recorren sus hijos.
Ninguna otra carpeta oculta se excluye automáticamente.

Sufijos de archivo excluidos por coincidencia exacta:

```text
.zip .7z .rar .exe .dll .iso .img .bin .pyc .log
```

No hay patrones glob adicionales, exclusión por prefijo, exclusión de
`Backups` ni límite por tamaño de archivo. El texto procesado se limita a
300.000 caracteres por documento; es truncamiento defensivo, no exclusión por
tamaño.

El recorrido recursivo no tiene límite fijo de profundidad. Usa IDs visitados
para controlar ciclos, permanece bajo `root_folder_id` mediante el cliente
OAuth y termina defensivamente por `max_items` —500 por defecto en el comando,
configurable hasta 5.000— y `folder_limit` —100 por defecto, hasta 1.000—. Si
alcanza un límite o un listado parece truncado, no infiere eliminaciones. El
límite de profundidad 20 pertenece solo a la representación `tree`, no a la
sincronización.

### Matriz de tipos

| Tipo | Estructura/navegación | Extracción textual actual | Índice léxico/semántico |
|---|---|---|---|
| Google Docs | Sí | Exportación a texto | Sí |
| Google Sheets | Sí | Exportación CSV | Sí |
| Google Slides | Sí | Exportación a texto | Sí |
| TXT, Markdown y otros `text/*` | Sí | UTF-8/Latin-1 controlado | Sí, salvo sufijo excluido |
| JSON, LD+JSON, XML, YAML | Sí | Texto | Sí |
| PDF | Sí | No en el cliente actual | No |
| DOCX, XLSX, PPTX | Sí | No en el cliente actual | No |
| Imágenes y vídeos | Sí | No | No |
| ZIP, 7Z, RAR y copias binarias | Sí | No | No; sufijo registrado como excluido |
| Sin extensión | Sí | Depende del MIME | Sí si el MIME es compatible |
| Vacío | Sí | Se descarga una vez | Sin fragmentos; queda estado `empty` |

Las carpetas desconocidas son visibles, navegables y recorridas. Solo se omiten
por configuración explícita, MIME no compatible, sufijo excluido, estado vacío
o límite defensivo, conceptos que no se confunden entre sí.

### Preservación comprobada

- Actualizar únicamente `02 - PC` mantuvo idénticos IDs y hashes de `00`,
  `01`, `04`, `11` y `Releases`.
- Actualizar únicamente `11 - Backups` mantuvo idénticos `00`, `01`, `02`,
  `04` y `Releases`.
- Actualizar la carpeta profunda de nivel 5 mantuvo intacto el documento de su
  carpeta hermana.
- No hubo entradas eliminadas ni errores en esos ámbitos.

La validación detectó además que una pasada no recursiva de la raíz podía
retirar estados auxiliares de archivos vacíos de ramas descendientes. Se añadió
procedencia parental a esos estados y una prueba de regresión; los documentos
originales nunca se eliminaron.
