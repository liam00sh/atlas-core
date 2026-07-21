# Sprint 18.1 — Estabilización, autoinicio y escalado de Telegram

## Objetivo

- Cargar la configuración privada desde `.env` sin dependencias externas.
- Iniciar Telegram en segundo plano al entrar en Windows.
- Reiniciar el proceso automáticamente si termina con error.
- Mantener una única instancia mediante el bloqueo existente.
- Conservar la vinculación y preferencias por usuario.
- Permitir añadir futuros usuarios sin modificar código.

## Escalado de usuarios

No existe una lista codificada de Liam, Saray, Lidia o Noa. Cada cuenta se
vincula mediante `telegram_user_id -> atlas_user_id`. Para añadir otra persona:

1. Crear previamente su usuario Atlas.
2. La persona abre el mismo bot y envía `/start`.
3. Un propietario o administrador confirma el código para ese `atlas_user_id`.
4. La asociación, sesión, permisos, asistente y continuidad quedan aislados por usuario.

## Inicio automático

Se utiliza el Programador de tareas de Windows con inicio al iniciar sesión del
usuario. Se elige este mecanismo porque el proyecto está en la unidad `H:` y esa
unidad puede no existir antes del inicio de sesión. La tarea espera a que la ruta
esté disponible y se ejecuta oculta.

## Aplicación de cambios

- Cambios en archivos `.py`: reiniciar la tarea.
- Cambios persistentes de datos, memoria o preferencias: se leen según cada
  componente; no requieren reiniciar Telegram en la mayoría de casos.
- Cambio `/coco` o `/daxter`: persistente y visible entre interfaces; no requiere
  reinicio del proceso.
- No se reinicia ni reinstala la aplicación Telegram del móvil.
