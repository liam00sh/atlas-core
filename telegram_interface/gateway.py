"""Enrutado seguro de comandos y mensajes Telegram hacia Atlas."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from time import monotonic, perf_counter
from typing import Any

from telegram_interface.audit import TelegramAuditLogger
from telegram_interface.config import TelegramConfig
from telegram_interface.core_adapter import AtlasCoreAdapter
from telegram_interface.identity_linker import TelegramIdentityLinker
from telegram_interface.models import (
    GatewayResponse,
    TelegramAccountState,
    TelegramMessage,
    TelegramRequestContext,
)
from telegram_interface.rate_limiter import TelegramRateLimiter
from telegram_interface.session_manager import TelegramSessionManager
from telegram_interface.progress import append_response_time


PUBLIC_COMMANDS = frozenset({"start", "help", "status", "whoami", "cancel"})
PRIVATE_COMMANDS = frozenset({"assistant", "daxter", "coco", "unlink", "unlink_confirm"})


class TelegramGateway:
    def __init__(
        self,
        *,
        config: TelegramConfig,
        linker: TelegramIdentityLinker,
        sessions: TelegramSessionManager,
        core: AtlasCoreAdapter,
        audit: TelegramAuditLogger,
        permission_resolver=None,
        rate_limiter: TelegramRateLimiter | None = None,
        clock=monotonic,
    ) -> None:
        self.config = config
        self.linker = linker
        self.sessions = sessions
        self.core = core
        self.audit = audit
        self.permission_resolver = permission_resolver or (lambda _user: frozenset({"telegram.use"}))
        self.rate_limiter = rate_limiter or TelegramRateLimiter(config.rate_limit_per_minute)
        self.clock = clock
        self._processing_errors: dict[tuple[str, str], tuple[int, float]] = {}
        self._executor = ThreadPoolExecutor(max_workers=config.max_concurrent_operations, thread_name_prefix="atlas-telegram")

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def handle(self, message: TelegramMessage) -> GatewayResponse:
        started = perf_counter()
        audit_result = "ok"
        audit_error: str | None = None
        if message.chat_type != "private":
            return self._early_response(message, "Esta version de Atlas solo admite conversaciones privadas.", "rejected", "chat_type_denied", started)
        if not self.rate_limiter.allow(message.user.telegram_user_id, message.user.chat_id):
            return self._early_response(message, "Has enviado demasiados mensajes. Espera unos segundos.", "rate_limited", "rate_limit", started)
        if len(message.text) > self.config.max_input_characters:
            return self._early_response(message, "El mensaje es demasiado largo para procesarlo de forma segura.", "rejected", "input_too_long", started)
        with self.sessions.lock_for(message.user.telegram_user_id, message.user.chat_id):
            account = self.linker.get_account(message.user.telegram_user_id)
            state = TelegramAccountState(account.get("state", "unlinked"))
            atlas_user_id = account.get("atlas_user_id") if state is TelegramAccountState.LINKED else None
            command, argument = self._command(message.text)
            if command:
                response = self._handle_command(command, argument, message, state, atlas_user_id)
            elif state is not TelegramAccountState.LINKED or atlas_user_id is None:
                response = GatewayResponse(
                    "Esta cuenta no esta vinculada. Usa /start para obtener un codigo temporal."
                )
            else:
                permissions = frozenset(self.permission_resolver(atlas_user_id))
                if "telegram.use" not in {item.casefold() for item in permissions}:
                    response = GatewayResponse("Tu usuario no tiene permiso para utilizar Atlas desde Telegram.")
                elif message.media_type:
                    response = self._handle_media_message(message)
                elif not message.text.strip():
                    response = GatewayResponse("Escribe un mensaje para hablar con Atlas.")
                else:
                    # Las respuestas sociales deterministas no necesitan activar
                    # usuario, contexto ni Ollama. Así pueden salir por el lane
                    # rápido aunque el Core esté ocupado con una tarea pesada.
                    quick_handler = getattr(self.core, "quick_response", None)
                    quick = quick_handler(message.text, "Atlas") if callable(quick_handler) else None
                    if quick is not None:
                        response = GatewayResponse(quick)
                    else:
                        error_key = (message.user.telegram_user_id, message.user.chat_id)
                        error_count, cooldown_until = self._processing_errors.get(error_key, (0, 0.0))
                        if cooldown_until > self.clock():
                            self.audit.record(
                                action="message",
                                result="cooldown",
                                telegram_user_id=message.user.telegram_user_id,
                                chat_id=message.user.chat_id,
                                atlas_user_id=atlas_user_id,
                                personality=self.core.active_personality(atlas_user_id),
                                duration_ms=round((perf_counter() - started) * 1000, 3),
                                error_code="processing_cooldown",
                            )
                            return GatewayResponse("Atlas ha detectado varios errores. Espera unos segundos.")
                        personality = self.core.active_personality(atlas_user_id)
                        context = TelegramRequestContext(
                            channel="telegram",
                            atlas_user_id=atlas_user_id,
                            session_id=f"telegram:{message.user.telegram_user_id}:{message.user.chat_id}",
                            telegram_user_id=message.user.telegram_user_id,
                            chat_id=message.user.chat_id,
                            message_id=message.message_id,
                            timestamp=message.timestamp,
                            active_personality=personality,
                            authentication_state=state,
                            permissions=permissions,
                        )
                        future = self._executor.submit(self.core.process, message.text, context)
                        try:
                            result = future.result(timeout=self.config.processing_timeout_seconds)
                            self._processing_errors.pop(error_key, None)
                            response = GatewayResponse(str(result).strip() or "Atlas no ha generado una respuesta.")
                        except FutureTimeout:
                            future.cancel()
                            self._record_processing_error(error_key, error_count)
                            audit_result = "timeout"
                            audit_error = "core_timeout"
                            response = GatewayResponse("Atlas ha tardado demasiado en responder. Intentalo de nuevo.")
                        except Exception:
                            self._record_processing_error(error_key, error_count)
                            audit_result = "error"
                            audit_error = "core_error"
                            response = GatewayResponse("Atlas no pudo procesar el mensaje de forma segura.")
            elapsed_seconds = perf_counter() - started
            if command is None and response.text and elapsed_seconds >= 2.5:
                current_personality = (
                    self.core.active_personality(atlas_user_id)
                    if atlas_user_id else "Daxter"
                )
                response = GatewayResponse(
                    append_response_time(response.text, elapsed_seconds, current_personality),
                    parse_mode=response.parse_mode,
                    close_session=response.close_session,
                )
            self.audit.record(
                action=command or "message",
                result=audit_result,
                telegram_user_id=message.user.telegram_user_id,
                chat_id=message.user.chat_id,
                atlas_user_id=atlas_user_id,
                personality=self.core.active_personality(atlas_user_id) if atlas_user_id else None,
                duration_ms=round((perf_counter() - started) * 1000, 3),
                error_code=audit_error,
            )
            return response

    def _handle_media_message(self, message: TelegramMessage) -> GatewayResponse:
        """Gestiona medios en cuarentena y usa analizadores opcionales sin inventar."""
        media_names = {
            "photo": "una foto", "voice": "un audio de voz",
            "audio": "un archivo de audio", "video": "un vídeo",
            "document": "un documento", "animation": "una animación",
        }
        received = media_names.get(message.media_type, "un archivo")
        caption = " ".join(message.text.split()).strip()
        if message.media_status == "rejected_too_large":
            return GatewayResponse("El archivo supera el límite seguro configurado y no se ha descargado.")
        if message.media_status == "rejected_type":
            return GatewayResponse("Ese formato no está permitido por la política multimedia segura de Atlas.")
        if message.media_status and message.media_status != "quarantined":
            return GatewayResponse("He recibido el archivo, pero no he podido descargarlo de forma segura. No se ha guardado permanentemente.")
        analyzer = getattr(self.core, "analyze_media", None)
        if callable(analyzer) and message.local_path:
            try:
                result = analyzer(
                    local_path=message.local_path,
                    media_type=message.media_type,
                    mime_type=message.mime_type,
                    caption=caption,
                    user_id=message.user.telegram_user_id,
                )
                if result:
                    return GatewayResponse(str(result).strip())
            except Exception:
                pass
        if not caption:
            return GatewayResponse(
                f"He recibido {received} y lo he guardado temporalmente en cuarentena. Todavía no tengo conectado el análisis "
                "del contenido. Dime qué necesitas hacer con él y te guiaré sin inventar lo que contiene."
            )
        if message.media_type == "photo":
            # Un pie como «Mira, este es Funcio» describe la intención del usuario,
            # pero no demuestra visualmente identidad, propietario ni relaciones.
            if len(caption.split()) <= 12 and not caption.endswith("?"):
                return GatewayResponse(
                    f"He recibido la foto temporalmente y el pie: «{caption}». Entiendo que me estás "
                    "presentando lo que aparece en ella, pero todavía no puedo ver la imagen. "
                    "¿Quieres que recuerde esa descripción o necesitas ayuda con la foto?"
                )
            return GatewayResponse(
                f"He recibido la foto temporalmente con este pie: «{caption}». Todavía no puedo analizar "
                "visualmente la imagen, así que no voy a adivinar su contenido. "
                "Descríbeme el detalle que quieres revisar o dime qué necesitas hacer con ella."
            )
        if message.media_type in {"voice", "audio"}:
            return GatewayResponse(
                f"He recibido {received} temporalmente con el texto «{caption}», pero todavía no tengo "
                "conectada la transcripción. Puedes escribir lo esencial y te ayudo con ello."
            )
        return GatewayResponse(
            f"He recibido {received} temporalmente con el texto «{caption}». Todavía no puedo analizar "
            "automáticamente su contenido. Dime qué parte necesitas revisar."
        )

    def _early_response(
        self,
        message: TelegramMessage,
        text: str,
        result: str,
        error_code: str,
        started: float,
    ) -> GatewayResponse:
        self.audit.record(
            action="message",
            result=result,
            telegram_user_id=message.user.telegram_user_id,
            chat_id=message.user.chat_id,
            duration_ms=round((perf_counter() - started) * 1000, 3),
            error_code=error_code,
        )
        return GatewayResponse(text)

    def _record_processing_error(self, key: tuple[str, str], previous_count: int) -> None:
        count = previous_count + 1
        cooldown_until = self.clock() + 15.0 if count >= 3 else 0.0
        self._processing_errors[key] = (count, cooldown_until)

    @staticmethod
    def _command(text: str) -> tuple[str | None, str]:
        stripped = text.strip()
        if not stripped.startswith("/"):
            return None, ""
        head, _, argument = stripped.partition(" ")
        command = head[1:].split("@", 1)[0].casefold()
        return command, argument.strip()

    def _handle_command(
        self,
        command: str,
        argument: str,
        message: TelegramMessage,
        state: TelegramAccountState,
        atlas_user_id: str | None,
    ) -> GatewayResponse:
        if command not in PUBLIC_COMMANDS | PRIVATE_COMMANDS:
            return GatewayResponse("Comando desconocido. Usa /help para ver las opciones disponibles.")
        if command == "start":
            if state is TelegramAccountState.LINKED and atlas_user_id:
                personality = self.core.active_personality(atlas_user_id).capitalize()
                return GatewayResponse(f"Atlas esta vinculado a {atlas_user_id}. Asistente activo: {personality}.")
            if state in {TelegramAccountState.BLOCKED, TelegramAccountState.REVOKED}:
                return GatewayResponse("Esta cuenta no puede iniciar una vinculacion. Requiere revision local.")
            code = self.linker.request_code(message.user)
            return GatewayResponse(
                "Atlas es privado. Confirma este codigo desde una sesion local autorizada en los proximos "
                f"{self.config.link_code_ttl_seconds // 60} minutos:\n\n{code}\n\nNo compartas el codigo."
            )
        if command == "help":
            if state is not TelegramAccountState.LINKED:
                return GatewayResponse("Comandos disponibles: /start, /help, /status, /whoami y /cancel.")
            return GatewayResponse(
                "Comandos disponibles: /start, /help, /status, /whoami, /assistant, "
                "/daxter, /coco, /unlink y /cancel."
            )
        if command == "status":
            if state is TelegramAccountState.LINKED and atlas_user_id:
                return GatewayResponse(
                    f"Conexion con Atlas: activa. Vinculacion: linked. Usuario: {atlas_user_id}. "
                    f"Asistente: {self.core.active_personality(atlas_user_id).capitalize()}."
                )
            return GatewayResponse(f"Conexion con Atlas: activa. Vinculacion: {state.value}.")
        if command == "whoami":
            if state is TelegramAccountState.LINKED and atlas_user_id:
                return GatewayResponse(f"Estas vinculado al usuario {atlas_user_id}.")
            return GatewayResponse("Esta cuenta todavia no esta vinculada.")
        if command == "cancel":
            pending = self.linker.cancel_pending(message.user.telegram_user_id, message.user.chat_id)
            session = self.sessions.get(message.user.telegram_user_id, message.user.chat_id)
            self.sessions.clear(message.user.telegram_user_id, message.user.chat_id)
            return GatewayResponse("Operacion cancelada." if pending or session else "No hay ninguna operacion pendiente.")
        if state is not TelegramAccountState.LINKED or atlas_user_id is None:
            return GatewayResponse("Este comando requiere una cuenta vinculada.")
        if command == "assistant":
            return GatewayResponse(f"Asistente activo: {self.core.active_personality(atlas_user_id).capitalize()}.")
        if command in {"daxter", "coco"}:
            if self.core.change_personality(atlas_user_id, command):
                return GatewayResponse(f"Asistente activo cambiado a {command.capitalize()}.")
            return GatewayResponse("No se pudo cambiar el asistente.")
        if command == "unlink":
            self.sessions.set(message.user.telegram_user_id, message.user.chat_id, pending_action="unlink")
            return GatewayResponse("La desvinculacion no es inmediata. Escribe /unlink_confirm para confirmarla o /cancel.")
        if command == "unlink_confirm":
            session = self.sessions.get(message.user.telegram_user_id, message.user.chat_id)
            if session.get("pending_action") != "unlink":
                return GatewayResponse("No hay una desvinculacion pendiente.")
            unlinked = self.linker.unlink(message.user.telegram_user_id, message.user.chat_id)
            self.sessions.clear(message.user.telegram_user_id, message.user.chat_id)
            return GatewayResponse("La cuenta Telegram ha sido desvinculada de Atlas.", close_session=True) if unlinked else GatewayResponse("No se pudo completar la desvinculacion.")
        return GatewayResponse("Comando no disponible.")
