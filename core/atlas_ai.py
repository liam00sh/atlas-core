"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_ai.py

Descripción:
    Contiene la lógica de inteligencia artificial utilizada por Atlas.

    Incluye:

    - Gestión de contextos temporales por interlocutor.
    - Construcción del prompt.
    - Obtención de información real del sistema.
    - Comunicación con el proveedor de IA.
    - Consulta y administración de contextos conversacionales.

    Esta clase se utiliza como mixin de la clase principal Atlas.
===============================================================================
"""
import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher

from ai.context.context_manager import AIContextManager

from core.log_manager import info
from core.system_info import format_system_info_for_ai
from core.system_info import get_system_info

from conversation.personality import private_context_denied

from utils.text_normalizer import normalize_text


class AtlasAIMixin:
    """
    Añade a Atlas las funciones relacionadas con IA local.
    """

    @staticmethod
    def _normalize_ai_context_user(
        user: str,
    ) -> str:
        """
        Normaliza un nombre para utilizarlo como clave de contexto.
        """

        if not isinstance(user, str):

            raise TypeError(
                "El usuario del contexto debe ser texto."
            )

        normalized_user = user.strip().casefold()

        if not normalized_user:

            raise ValueError(
                "El usuario del contexto no puede estar vacío."
            )

        return normalized_user

    def _get_current_conversation_user(
        self,
    ) -> str:
        """
        Devuelve la persona que está hablando actualmente.

        Si todavía no existe una identidad conversacional
        reconocida, utiliza el usuario autenticado.
        """

        conversation_identity = getattr(
            self,
            "conversation_identity",
            None,
        )

        if conversation_identity is None:
            return self.get_user()

        conversation_user = (
            conversation_identity
            .get_conversation_owner()
        )

        if conversation_user is None:
            return self.get_user()

        return conversation_user

    def _get_ai_context_for_user(
        self,
        user: str,
    ) -> AIContextManager:
        """
        Devuelve el contexto temporal de un usuario.

        Si todavía no existe, lo crea automáticamente.
        """

        context_key = self._normalize_ai_context_user(
            user
        )

        if context_key not in self.ai_contexts:

            self.ai_contexts[context_key] = (
                AIContextManager(
                    max_messages=(
                        self.ai_context_max_messages
                    )
                )
            )

            info(
                f"Contexto temporal de IA creado "
                f"para {user}."
            )

        return self.ai_contexts[
            context_key
        ]

    def get_current_ai_context(
        self,
    ) -> AIContextManager:
        """
        Devuelve el contexto temporal de la persona
        que está hablando actualmente.

        El contexto pertenece al interlocutor real,
        no necesariamente al usuario autenticado.
        """

        current_conversation_user = (
            self._get_current_conversation_user()
        )

        return self._get_ai_context_for_user(
            current_conversation_user
        )

    def _handle_user_context_query(
        self,
        original_text: str,
    ) -> bool:
        """
        Detecta consultas sobre la conversación temporal
        de otro usuario.

        Ejemplos reconocidos:

            de qué estabas hablando con Saray
            de qué hablabas con Saray
            qué hablaste con Saray
            qué ha hablado Saray
            conversación de Saray
            conversación Saray
            contexto de Saray
            contexto Saray
            contecto Saray

        Devuelve:
            True:
                La consulta ha sido reconocida y procesada.

            False:
                No era una consulta sobre el contexto
                de otro usuario.
        """

        normalized_text = normalize_text(
            original_text
        )

        prefixes = (
            "de que estabas hablando con ",
            "de que hablabas con ",
            "que estabas hablando con ",
            "que hablabas con ",
            "que hablaste con ",
            "que has hablado con ",
            "que ha hablado ",
            "conversacion de ",
            "conversacion ",
            "contexto de ",
            "contexto ",
            "que sabes de la conversacion de ",
            "que sabes del contexto de ",
        )

        requested_user = None

        for prefix in prefixes:

            if normalized_text.startswith(
                prefix
            ):

                requested_user = normalized_text[
                    len(prefix):
                ].strip()

                break

        # La entrada no era una consulta de contexto.
        if not requested_user:
            return False

        resolved_user = self.users.resolve_user_name(
            requested_user
        )

        if resolved_user is None:

            print()

            print(
                f"No conozco ningún usuario llamado "
                f"«{requested_user}»."
            )

            return True

        summary = self.summarize_ai_context_for_user(
            resolved_user
        )

        # None significa que el usuario activo
        # no tiene permiso para acceder.
        if summary is None:

            grammatical_gender = (
                self.get_user_grammatical_gender(
                    resolved_user
                )
            )

            print()

            print(
                private_context_denied(
                    requested_user=resolved_user,
                    grammatical_gender=grammatical_gender,
                )
            )

            return True

        # Cadena vacía significa que sí tiene permiso,
        # pero no hay conversación guardada.
        if not summary:

            print()

            print(
                f"No tengo ninguna conversación temporal "
                f"guardada con {resolved_user}."
            )

            return True

        print()

        print(summary)

        return True

    @staticmethod
    def _normalize_entity_text(
        value: str,
    ) -> str:
        """Normaliza texto para localizar nombres y alias sin acentos."""

        normalized = unicodedata.normalize(
            "NFD",
            str(value).casefold(),
        )

        normalized = "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Mn"
        )

        normalized = re.sub(
            r"[^\w\s]",
            " ",
            normalized,
        )

        return re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

    def _person_relationship_text(self, person) -> str:
        """Devuelve relaciones verificadas en un texto normalizado."""

        relationships = (
            self.relationship_engine
            .describe_relationships_for_entity(
                entity_id=person.id,
                entity_type="person",
            )
        )

        return self._normalize_entity_text(
            " ".join(relationships or [])
        )

    def _find_entities_mentioned(
        self,
        user_message: str,
    ) -> list[tuple[str, object]]:
        """Localiza entidades mencionadas, priorizando la referencia más larga."""

        normalized = self._normalize_entity_text(user_message)
        matches = []

        entity_groups = (
            ("person", self.people_manager.get_people()),
            ("animal", self.people_manager.get_animals()),
        )

        for entity_type, entities in entity_groups:
            for entity in entities:
                references = [
                    entity.name,
                    *getattr(entity, "aliases", []),
                ]
                for reference in references:
                    normalized_reference = self._normalize_entity_text(reference)
                    if not normalized_reference:
                        continue
                    match = re.search(
                        rf"(?<!\w){re.escape(normalized_reference)}(?!\w)",
                        normalized,
                    )
                    if match:
                        matches.append(
                            (
                                match.start(),
                                match.end(),
                                len(normalized_reference),
                                entity_type,
                                entity,
                            )
                        )

        # Una aclaración resuelta debe imponerse sobre el nombre ambiguo
        # que aparecía en la pregunta original.
        resolved_id = getattr(self, "_resolved_entity_id", None)
        if resolved_id:
            resolved = [
                (entity_type, entity)
                for _, _, _, entity_type, entity in matches
                if entity.id == resolved_id
            ]
            if resolved:
                return resolved[:1]

        if not matches:
            return []

        # Si varias referencias empiezan en la misma posición, se conserva
        # únicamente la más específica. Así «José Miguel» no se reduce a «José».
        best_length_by_start = {}
        for start, _, length, _, _ in matches:
            best_length_by_start[start] = max(
                length,
                best_length_by_start.get(start, 0),
            )

        filtered = [
            item for item in matches
            if item[2] == best_length_by_start[item[0]]
        ]
        filtered.sort(key=lambda item: (item[0], -item[2]))

        result = []
        seen = set()
        for _, _, _, entity_type, entity in filtered:
            key = (entity_type, entity.id)
            if key in seen:
                continue
            seen.add(key)
            result.append((entity_type, entity))
        return result

    @staticmethod
    def _join_names(names: list[str]) -> str:
        """Une una lista de nombres con gramática española sencilla."""

        names = [name for name in names if name]
        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        return ", ".join(names[:-1]) + " y " + names[-1]

    def _entity_by_id(self, entity_id: str):
        """Recupera una persona o animal sin depender de métodos opcionales."""

        for entity in [
            *self.people_manager.get_people(),
            *self.people_manager.get_animals(),
        ]:
            if entity.id == entity_id:
                return entity
        return None

    def _active_assistant_and_mode(self) -> tuple[str, str]:
        """Obtiene identidad y modo activos sin acoplarse a una sola API."""

        manager = getattr(self, "identity_manager", None)
        identity = "Daxter"
        mode = "classic"
        if manager is None:
            return identity, mode

        for method_name in (
            "get_active_display_name",
            "get_active_identity_name",
        ):
            method = getattr(manager, method_name, None)
            if callable(method):
                value = method()
                if value:
                    identity = str(value)
                    break

        for method_name in (
            "get_active_mode_name",
            "get_current_mode_name",
            "get_active_mode",
            "get_current_mode",
        ):
            method = getattr(manager, method_name, None)
            if not callable(method):
                continue
            value = method()
            if value is None:
                continue
            mode = str(getattr(value, "name", value))
            break

        return (
            self._normalize_entity_text(identity),
            self._normalize_entity_text(mode),
        )

    def _style_verified_response(
        self,
        factual_response: str,
        *,
        response_kind: str = "fact",
    ) -> str:
        """Da voz a una respuesta verificada sin alterar sus hechos."""

        text = str(factual_response or "").strip()
        if not text:
            return text

        identity, mode = self._active_assistant_and_mode()
        is_coco = "coco" in identity

        if "trabajo" in mode or "work" in mode:
            opener = "Vamos con los datos verificados:"
        elif "empatic" in mode or "empathetic" in mode:
            opener = "Claro, te lo cuento con calma:"
        elif "divertid" in mode or "fun" in mode or "fiesta" in mode:
            opener = (
                "Vale, ficha rápida y sin montar un drama:"
                if not is_coco
                else "Venga, te lo cuento de forma sencilla:"
            )
        elif is_coco:
            opener = "Claro, te cuento:"
        elif response_kind == "biography":
            opener = "Vale, te pongo en situación:"
        elif response_kind == "relationship":
            opener = "Vamos al grano:"
        else:
            opener = "Vale, dato confirmado:"

        return f"{opener} {text}"

    def _answer_verified_entity_query(
        self,
        user_message: str,
    ) -> str | None:
        """
        Responde de forma determinista a consultas factuales sencillas.

        Las relaciones y biografías verificadas no deben dejarse a la
        improvisación del modelo local. El modelo sigue utilizándose para
        conversación general, pero estas preguntas se resuelven con el grafo.
        """

        normalized = self._normalize_entity_text(user_message)
        mentioned = self._find_entities_mentioned(user_message)

        if mentioned:
            self._last_factual_entity_id = mentioned[-1][1].id

        # Consultas explícitas entre dos entidades.
        pair_markers = (
            "que relacion tiene",
            "que relacion hay",
            "relacion entre",
            "quien es",
            "para ",
            "incluidas las ocultas",
            "incluidas las privadas",
        )
        if len(mentioned) >= 2 and any(marker in normalized for marker in pair_markers):
            source_type, source = mentioned[0]
            target_type, target = mentioned[1]
            description = (
                self.relationship_engine
                .describe_relationship_between_entities(
                    source_entity_id=source.id,
                    source_entity_type=source_type,
                    target_entity_id=target.id,
                    target_entity_type=target_type,
                )
            )
            if description:
                return description

        # Consultas de familiares de una persona.
        relation_specs = (
            (
                ("quienes son los padres", "quien son los padres", "mis padres"),
                {"padre", "madre"},
                "Los padres de {subject} son {names}.",
                {"padre": 0, "madre": 1},
            ),
            (
                ("quienes son los hermanos", "quien son los hermanos", "mis hermanos"),
                {"hermano", "hermana"},
                "Los hermanos de {subject} son {names}.",
                {"hermano": 0, "hermana": 1},
            ),
            (
                ("quien es la madre", "madre de "),
                {"madre"},
                "La madre de {subject} es {names}.",
                {"madre": 0},
            ),
            (
                ("quien es el padre", "padre de "),
                {"padre"},
                "El padre de {subject} es {names}.",
                {"padre": 0},
            ),
            (
                (
                    "quien es la pareja",
                    "pareja de ",
                    "con quien esta",
                    "con quien sale",
                ),
                {"pareja", "esposo", "esposa"},
                "La pareja de {subject} es {names}.",
                {"pareja": 0, "esposo": 0, "esposa": 0},
            ),
        )

        for markers, labels, template, order in relation_specs:
            if not any(marker in normalized for marker in markers):
                continue

            subject = None
            for entity_type, entity in reversed(mentioned):
                if entity_type == "person":
                    subject = entity
                    break

            if subject is None and (
                "mis " in normalized
                or normalized.startswith("mi ")
            ):
                subject = self.people_manager.find_person_by_name(
                    self._get_current_conversation_user()
                )

            if subject is None:
                return None

            matches = []
            for candidate in self.people_manager.get_people():
                if candidate.id == subject.id:
                    continue
                label = self.relationship_engine.infer_relationship_label(
                    source_entity_id=candidate.id,
                    source_entity_type="person",
                    target_entity_id=subject.id,
                    target_entity_type="person",
                )
                normalized_label = self._normalize_entity_text(label or "")
                if normalized_label in labels:
                    matches.append(
                        (
                            order.get(normalized_label, 99),
                            candidate.name,
                        )
                    )

            matches.sort(key=lambda item: (item[0], item[1]))
            names = self._join_names([name for _, name in matches])
            if not names:
                return (
                    f"No tengo una relación verificada de ese tipo para "
                    f"{subject.name}."
                )
            return template.format(subject=subject.name, names=names)

        # Fichas y datos biográficos. Los seguimientos cortos usan la última
        # entidad seleccionada de forma explícita, no todo el historial.
        biography_markers = (
            "quien es ",
            "quien era ",
            "hablame de ",
            "cuentame sobre ",
            "que sabes de ",
            "donde nacio",
            "donde vive",
            "donde ha vivido",
            "cuando nacio",
            "cumpleanos",
            "en que trabaja",
            "donde trabaja",
            "que hacia",
            "que estudio",
            "que ha estudiado",
        )
        if any(marker in normalized for marker in biography_markers):
            entity = mentioned[-1][1] if mentioned else None
            if entity is None:
                last_id = getattr(self, "_last_factual_entity_id", None)
                if last_id:
                    entity = self._entity_by_id(last_id)
            if entity is None:
                return None

            summary = str(getattr(entity, "summary", "") or "").strip()
            if not summary:
                return f"No tengo datos biográficos verificados sobre {entity.name}."

            sentences = [
                sentence.strip()
                for sentence in re.split(r"(?<=[.!?])\s+", summary)
                if sentence.strip()
            ]
            keyword_groups = []
            if "donde " in normalized:
                keyword_groups = ["nacio", "vive", "vivio", "ha vivido", "rumania", "albacete"]
            elif "cuando nacio" in normalized or "cumpleanos" in normalized:
                keyword_groups = ["cumpleanos"]
            elif "trabaja" in normalized:
                keyword_groups = ["trabaja", "trabajo", "ha trabajado", "trabajó"]
            elif "que hacia" in normalized:
                keyword_groups = ["joven", "bailarin", "bailarín"]
            elif "estudio" in normalized or "estudiado" in normalized:
                keyword_groups = ["estudio", "estudió", "ha estudiado", "educacion", "administracion"]

            if keyword_groups:
                selected = [
                    sentence for sentence in sentences
                    if any(
                        keyword in self._normalize_entity_text(sentence)
                        for keyword in keyword_groups
                    )
                ]
                if selected:
                    return " ".join(selected)

            return summary

        return None

    @staticmethod
    def _ordered_token_span(
        query_tokens: list[str],
        reference_tokens: list[str],
    ) -> int | None:
        """Devuelve el menor tramo que contiene los tokens en el mismo orden."""

        if not query_tokens or not reference_tokens:
            return None

        positions = []
        search_from = 0
        for token in query_tokens:
            try:
                position = reference_tokens.index(token, search_from)
            except ValueError:
                return None
            positions.append(position)
            search_from = position + 1

        return positions[-1] - positions[0] + 1

    def _extract_requested_person_reference(
        self,
        user_message: str,
    ) -> str:
        """Extrae el nombre solicitado de una pregunta biográfica habitual."""

        normalized = self._normalize_entity_text(user_message)
        patterns = (
            r"^(?:quien es|quien era|quienes son|hablame de|cuentame sobre|que sabes de)\s+(.+?)$",
            r"^(?:donde vive|donde nacio|cuando nacio|en que trabaja|donde trabaja)\s+(.+?)$",
        )
        for pattern in patterns:
            match = re.match(pattern, normalized)
            if match:
                return match.group(1).strip(" .?!¡¿")
        return ""

    def _people_matching_reference(
        self,
        requested_reference: str,
    ) -> list:
        """
        Resuelve referencias parciales sin confundir nombres compuestos.

        Reglas:
        - «José» devuelve todos los José.
        - «José Miguel» devuelve solo José Miguel.
        - «José Vicente» devuelve José Vicente y José Vicente Navarro.
        - «Sara» no coincide con Saray.
        - Una combinación no contigua usa el candidato con menor separación.
        """

        requested = self._normalize_entity_text(requested_reference)
        if not requested:
            return []
        query_tokens = requested.split()

        people = self.people_manager.get_people()
        exact = []
        prefix = []
        subsequence = []

        for person in people:
            primary = self._normalize_entity_text(person.name)
            aliases = {
                self._normalize_entity_text(alias)
                for alias in getattr(person, "aliases", [])
                if self._normalize_entity_text(alias)
            }
            references = [primary, *sorted(aliases)]

            if requested in references:
                exact.append(person)

            # Los prefijos se calculan sobre el nombre principal. Esto permite
            # que «José Vicente» incluya también «José Vicente Navarro».
            primary_tokens = primary.split()
            if primary_tokens[:len(query_tokens)] == query_tokens:
                prefix.append(person)

            best_span = None
            for reference in references:
                reference_tokens = reference.split()
                if (
                    not reference_tokens
                    or reference_tokens[0] != query_tokens[0]
                ):
                    continue
                span = self._ordered_token_span(query_tokens, reference_tokens)
                if span is not None and (best_span is None or span < best_span):
                    best_span = span
            if best_span is not None:
                subsequence.append((best_span, person))

        def unique(items):
            return list({person.id: person for person in items}.values())

        prefix = unique(prefix)
        exact = unique(exact)

        # Aunque exista una coincidencia exacta, un nombre puede ser prefijo
        # completo de otra persona: «José Vicente» debe ofrecer ambas.
        if prefix:
            return sorted(prefix, key=lambda person: person.name.casefold())
        if exact:
            return sorted(exact, key=lambda person: person.name.casefold())

        if not subsequence:
            return []
        best_span = min(span for span, _ in subsequence)
        best = unique([
            person for span, person in subsequence
            if span == best_span
        ])
        return sorted(best, key=lambda person: person.name.casefold())

    def _find_ambiguous_person_reference(
        self,
        user_message: str,
    ):
        """Detecta una referencia que sigue identificando a varias personas."""

        requested = self._extract_requested_person_reference(user_message)
        if requested:
            candidates = self._people_matching_reference(requested)
            if len(candidates) > 1:
                return requested, candidates
            return None

        # Respaldo para preguntas con una redacción menos previsible.
        normalized_message = self._normalize_entity_text(user_message)
        reference_map = {}
        for person in self.people_manager.get_people():
            references = [
                person.name.split()[0],
                *getattr(person, "aliases", []),
            ]
            for reference in references:
                normalized_reference = self._normalize_entity_text(reference)
                if normalized_reference:
                    reference_map.setdefault(normalized_reference, []).append(person)

        matches = []
        for reference, candidates in reference_map.items():
            candidates = list({p.id: p for p in candidates}.values())
            if len(candidates) < 2:
                continue
            if re.search(
                rf"(?<!\w){re.escape(reference)}(?!\w)",
                normalized_message,
            ):
                matches.append((reference, candidates))

        if not matches:
            return None
        return max(matches, key=lambda item: len(item[0]))

    @staticmethod
    def _parse_ordinal_selection(answer: str) -> int | None:
        """Convierte respuestas ordinales naturales en un índice cero-based."""

        normalized = re.sub(r"\s+", " ", str(answer).casefold()).strip()
        normalized = re.sub(r"^(?:el|la)\s+", "", normalized)

        ordinal_groups = (
            {"1", "uno", "una", "primero", "primera"},
            {"2", "dos", "segundo", "segunda"},
            {"3", "tres", "tercero", "tercera"},
            {"4", "cuatro", "cuarto", "cuarta"},
            {"5", "cinco", "quinto", "quinta"},
        )

        for index, options in enumerate(ordinal_groups):
            if normalized in options:
                return index

        return None

    def _candidate_matches_speaker_relation(
        self,
        person,
        answer: str,
    ) -> bool:
        """Resuelve expresiones de parentesco desde quien está hablando."""

        normalized_answer = self._normalize_entity_text(answer)
        relation_aliases = {
            "madre": {"madre", "mama"},
            "padre": {"padre", "papa"},
            "hija": {"hija"},
            "hijo": {"hijo"},
            "hermana": {"hermana"},
            "hermano": {"hermano"},
            "tia": {"tia"},
            "tio": {"tio"},
            "sobrina": {"sobrina"},
            "sobrino": {"sobrino"},
            "abuela": {"abuela"},
            "abuelo": {"abuelo"},
            "nieta": {"nieta"},
            "nieto": {"nieto"},
            "prima": {"prima"},
            "primo": {"primo"},
            "pareja": {"pareja", "novia", "novio"},
            "cunada": {"cunada"},
            "cunado": {"cunado"},
            "suegra": {"suegra"},
            "suegro": {"suegro"},
            "nuera": {"nuera"},
            "yerno": {"yerno"},
            "mascota": {"mascota", "animal"},
            "propietario": {"propietario", "dueno", "dueño"},
            "cuidador": {"cuidador", "cuidadora"},
        }

        answer_tokens = set(normalized_answer.split())
        requested = {
            canonical
            for canonical, aliases in relation_aliases.items()
            if answer_tokens.intersection(aliases)
        }
        if not requested:
            return False

        speaker = self.people_manager.find_person_by_name(
            self._get_current_conversation_user()
        )
        if speaker is None:
            return False

        inferred = self.relationship_engine.infer_relationship_label(
            source_entity_id=person.id,
            source_entity_type="person",
            target_entity_id=speaker.id,
            target_entity_type="person",
        )
        normalized_inferred = self._normalize_entity_text(inferred or "")
        if normalized_inferred:
            inferred_tokens = set(normalized_inferred.split())
            if any(
                canonical in inferred_tokens
                or aliases.intersection(inferred_tokens)
                for canonical, aliases in relation_aliases.items()
                if canonical in requested
            ):
                return True

        description = (
            self.relationship_engine
            .describe_relationship_between_entities(
                source_entity_id=person.id,
                source_entity_type="person",
                target_entity_id=speaker.id,
                target_entity_type="person",
            )
        )
        normalized_description = self._normalize_entity_text(description)
        return any(
            canonical in normalized_description
            or any(alias in normalized_description for alias in aliases)
            for canonical, aliases in relation_aliases.items()
            if canonical in requested
        )

    def _prepare_entity_clarification(
        self,
        original_text: str,
    ) -> tuple[str, bool]:
        """Gestiona preguntas ambiguas y su respuesta de seguimiento."""

        pending = getattr(
            self,
            "_pending_entity_clarification",
            None,
        )

        if pending is not None:
            normalized_answer = self._normalize_entity_text(original_text)
            people_by_id = {
                person.id: person
                for person in self.people_manager.get_people()
            }
            candidates = [
                people_by_id[candidate_id]
                for candidate_id in pending["candidate_ids"]
                if candidate_id in people_by_id
            ]
            resolved = []

            selected_index = self._parse_ordinal_selection(
                normalized_answer
            )

            if (
                selected_index is not None
                and 0 <= selected_index < len(candidates)
            ):
                resolved = [candidates[selected_index]]

            if not resolved:
                for person in candidates:
                    name_parts = [
                        part
                        for part in person.name.split()
                        if len(part) >= 3
                    ]
                    references = [
                        person.name,
                        *name_parts,
                        *getattr(person, "aliases", []),
                    ]
                    reference_match = any(
                        (
                            self._normalize_entity_text(reference)
                            == normalized_answer
                        )
                        or (
                            " " in self._normalize_entity_text(reference)
                            and re.search(
                                rf"(?<!\w){re.escape(self._normalize_entity_text(reference))}(?!\w)",
                                normalized_answer,
                            )
                        )
                        for reference in references
                        if self._normalize_entity_text(reference)
                    )
                    relationship_text = self._person_relationship_text(person)
                    stopwords = {
                        "a", "al", "de", "del", "el", "ella", "es",
                        "la", "las", "los", "su", "sus", "un", "una",
                    }
                    relation_word_aliases = {
                        "mujer": "pareja",
                        "esposa": "pareja",
                        "marido": "pareja",
                        "esposo": "pareja",
                    }
                    answer_tokens = {
                        relation_word_aliases.get(token, token)
                        for token in normalized_answer.split()
                        if token not in stopwords and len(token) >= 3
                    }
                    relationship_tokens = set(
                        relationship_text.split()
                    )
                    relationship_match = (
                        bool(answer_tokens)
                        and answer_tokens.issubset(
                            relationship_tokens
                        )
                    )

                    fuzzy_match = False
                    ambiguous_reference_tokens = set(
                        self._normalize_entity_text(
                            pending.get("reference", "")
                        ).split()
                    )
                    answer_words = [
                        token for token in normalized_answer.split()
                        if (
                            len(token) >= 4
                            and token not in ambiguous_reference_tokens
                        )
                    ]
                    candidate_words = [
                        self._normalize_entity_text(part)
                        for part in person.name.split()
                        if (
                            len(part) >= 4
                            and self._normalize_entity_text(part)
                            not in ambiguous_reference_tokens
                        )
                    ]
                    for answer_word in answer_words:
                        if any(
                            SequenceMatcher(
                                None,
                                answer_word,
                                candidate_word,
                            ).ratio() >= 0.78
                            for candidate_word in candidate_words
                        ):
                            fuzzy_match = True
                            break

                    speaker_relation_match = (
                        self._candidate_matches_speaker_relation(
                            person,
                            normalized_answer,
                        )
                    )

                    relation_only_tokens = {
                        "mi", "mis", "su", "sus", "la", "el", "de",
                        "madre", "mama", "padre", "papa", "hermana",
                        "hermano", "tia", "tio", "abuela", "abuelo",
                        "prima", "primo", "pareja", "novia", "novio",
                        "cunada", "cunado", "suegra", "suegro",
                        "nuera", "yerno", "sobrina", "sobrino",
                        "nieta", "nieto", "hija", "hijo",
                        "mascota", "animal", "propietario", "dueno",
                        "cuidador", "cuidadora",
                        "mujer", "esposa", "marido", "esposo",
                    }
                    if set(normalized_answer.split()).issubset(relation_only_tokens):
                        relationship_match = False
                        fuzzy_match = False

                    if (
                        reference_match
                        or relationship_match
                        or fuzzy_match
                        or speaker_relation_match
                    ):
                        resolved.append(person)

            unique_resolved = {
                person.id: person
                for person in resolved
            }

            if len(unique_resolved) == 1:
                selected = next(iter(unique_resolved.values()))
                self._resolved_entity_id = selected.id
                self._resolved_entity_candidate_ids = set(
                    pending["candidate_ids"]
                )
                self._pending_entity_clarification = None
                self._last_factual_entity_id = selected.id

                correction = ""
                selected_words = {
                    self._normalize_entity_text(part)
                    for part in selected.name.split()
                    if len(part) >= 4
                }
                answer_words = {
                    token for token in normalized_answer.split()
                    if len(token) >= 4
                }
                if answer_words and not answer_words.intersection(selected_words):
                    correction = (
                        f"Has escrito «{original_text.strip()}»; es posible que "
                        f"te refieras a «{selected.name}». "
                    )

                rewritten = (
                    f"{pending['original_question']}\n"
                    f"{correction}Aclaración: me refiero a {selected.name}."
                )
                return rewritten, False

            options = " o ".join(
                person.name
                for person in candidates
            )
            print()
            print(
                "No he podido saber cuál eliges. "
                f"Puedes responder primero/primera, segundo/segunda, "
                f"con un nombre o apellido, o por su relación. "
                f"Las opciones son {options}."
            )
            return original_text, True

        requested_reference = self._extract_requested_person_reference(
            original_text
        )
        if requested_reference:
            direct_candidates = self._people_matching_reference(
                requested_reference
            )
            if len(direct_candidates) == 1:
                selected = direct_candidates[0]
                self._resolved_entity_id = selected.id
                self._resolved_entity_candidate_ids = {selected.id}
                self._last_factual_entity_id = selected.id
                return (
                    f"{original_text}\n"
                    f"Referencia resuelta internamente: {selected.name}.",
                    False,
                )

        ambiguous = self._find_ambiguous_person_reference(original_text)

        if ambiguous is None:
            normalized_question = self._normalize_entity_text(original_text)
            match = re.search(
                r"(?:quien es|quien era|hablame de|cuentame sobre|que sabes de)\s+([a-z0-9_]+)",
                normalized_question,
            )
            if match:
                requested_name = match.group(1)
                exact_known = []
                fuzzy_known = []
                for person in self.people_manager.get_people():
                    references = [person.name.split()[0], *getattr(person, "aliases", [])]
                    normalized_references = {
                        self._normalize_entity_text(reference)
                        for reference in references
                        if self._normalize_entity_text(reference)
                    }
                    if requested_name in normalized_references:
                        exact_known.append(person)
                        continue
                    best = max(
                        (SequenceMatcher(None, requested_name, reference).ratio() for reference in normalized_references),
                        default=0.0,
                    )
                    if best >= 0.72:
                        fuzzy_known.append((best, person))

                if not exact_known and fuzzy_known:
                    fuzzy_known.sort(key=lambda item: item[0], reverse=True)
                    best_score = fuzzy_known[0][0]
                    best_people = [
                        person for score, person in fuzzy_known
                        if best_score - score <= 0.03
                    ]
                    if best_score >= 0.80 and len(best_people) == 1:
                        selected = best_people[0]
                        rewritten = re.sub(
                            rf"(?<!\w){re.escape(match.group(1))}(?!\w)",
                            selected.name,
                            original_text,
                            count=1,
                            flags=re.IGNORECASE,
                        )
                        return (
                            rewritten
                            + f"\nAclaración: «{match.group(1)}» parece una errata de «{selected.name}».",
                            False,
                        )

                    options = " o ".join(person.name for person in best_people)
                    print()
                    print(
                        f"No conozco a nadie llamado {match.group(1).title()}. "
                        f"¿Es una persona nueva o querías decir {options}?"
                    )
                    return original_text, True

            return original_text, False

        reference, candidates = ambiguous
        self._pending_entity_clarification = {
            "reference": reference,
            "original_question": original_text,
            "candidate_ids": [person.id for person in candidates],
        }
        options = " y ".join(
            person.name
            for person in candidates
        )

        print()
        print(
            f"Conozco a {len(candidates)} personas llamadas "
            f"{reference.title()}: {options}. ¿A cuál te refieres?"
        )
        return original_text, True

    def _build_speaker_relationship_context(
        self,
        entity,
        entity_type: str,
    ) -> list[str]:
        """Describe la entidad desde la perspectiva del interlocutor real."""

        speaker_name = self._get_current_conversation_user()
        speaker = self.people_manager.find_person_by_name(speaker_name)

        if speaker is None:
            return [
                f"Interlocutor actual: {speaker_name}.",
                "Habla siempre al interlocutor en segunda persona.",
            ]

        lines = [
            f"Interlocutor actual: {speaker.name}.",
            (
                "Describe las relaciones desde el punto de vista de "
                f"{speaker.name}: usa «tu» para una relación directa con "
                "quien pregunta; nunca uses «mi» para relaciones familiares "
                "o sentimentales del interlocutor. Si la entidad es pareja "
                "del interlocutor, di «tu pareja». Si el interlocutor es hermano "
                "o hermana de la pareja, puedes decir «tu cuñada» o «tu cuñado» "
                "y aclarar la cadena real. No inventes parentescos como primo o prima."
            ),
        ]

        relationship_description = (
            self.relationship_engine
            .describe_relationship_between_entities(
                source_entity_id=entity.id,
                source_entity_type=entity_type,
                target_entity_id=speaker.id,
                target_entity_type="person",
            )
        )

        if relationship_description:
            lines.append(
                "Relación verificada con quien pregunta:"
            )
            lines.append(f"- {relationship_description}")
            lines.append(
                "Usa la etiqueta familiar inferida cuando exista. Si solo "
                "hay una cadena verificable, explica la cadena y no inventes "
                "un parentesco más específico."
            )

        return lines

    def _build_referenced_entities_context(
        self,
        user_message: str,
    ) -> str:
        """
        Añade datos verificables de personas y animales mencionados.

        Mencionar a Saray, Pepi o cualquier otra entidad no cambia quién está
        hablando. Este contexto permite responder relaciones familiares desde
        el punto de vista del interlocutor real.
        """

        normalized_message = self._normalize_entity_text(
            user_message
        )

        if not normalized_message:
            return ""

        sections = []
        matched_entities = []

        for person in self.people_manager.get_people():
            references = [
                person.name,
                *getattr(person, "aliases", []),
            ]

            matched = any(
                re.search(
                    rf"(?<!\w){re.escape(self._normalize_entity_text(reference))}(?!\w)",
                    normalized_message,
                )
                for reference in references
                if self._normalize_entity_text(reference)
            )

            if not matched:
                continue

            resolved_candidate_ids = getattr(
                self,
                "_resolved_entity_candidate_ids",
                set(),
            )
            resolved_entity_id = getattr(
                self,
                "_resolved_entity_id",
                None,
            )

            if (
                person.id in resolved_candidate_ids
                and person.id != resolved_entity_id
            ):
                continue

            preferred_name = (
                person.aliases[0]
                if getattr(person, "aliases", [])
                else person.name.split()[0]
            )
            lines = [
                f"Persona mencionada: {person.name}.",
                f"Nombre habitual preferido: {preferred_name}.",
                "La consulta trata sobre una sola persona: usa tercera persona singular.",
                "Revisa concordancia, verbos, posesivos y pronombres antes de responder.",
                "Si hay datos sensibles, no los menciones salvo que el usuario los haya introducido expresamente.",
                (
                    "No antepongas artículos al nombre propio: di "
                    f"«{preferred_name}», nunca «el {preferred_name}» ni "
                    f"«la {preferred_name}»."
                ),
                (
                    "Perfil de usuario asociado: "
                    f"{person.user_profile or 'ninguno'}."
                ),
            ]
            lines.extend(
                self._build_speaker_relationship_context(
                    person,
                    "person",
                )
            )

            if person.summary:
                lines.append(
                    f"Resumen verificado: {person.summary}"
                )

            relationships = (
                self.relationship_engine
                .describe_relationships_for_entity(
                    entity_id=person.id,
                    entity_type="person",
                )
            )

            if relationships:
                lines.append(
                    "Relaciones verificadas:"
                )
                lines.extend(
                    f"- {relationship}"
                    for relationship in relationships
                )

            sections.append("\n".join(lines))
            matched_entities.append(("person", person))

        for animal in self.people_manager.get_animals():
            references = [
                animal.name,
                *getattr(animal, "aliases", []),
            ]

            matched = any(
                re.search(
                    rf"(?<!\w){re.escape(self._normalize_entity_text(reference))}(?!\w)",
                    normalized_message,
                )
                for reference in references
                if self._normalize_entity_text(reference)
            )

            if not matched:
                continue

            preferred_name = (
                animal.aliases[0]
                if getattr(animal, "aliases", [])
                else animal.name
            )
            lines = [
                f"Animal mencionado: {animal.name}.",
                f"Nombre habitual preferido: {preferred_name}.",
                "La consulta trata sobre un solo animal: usa tercera persona singular.",
                (
                    "Usa siempre el nombre habitual sin artículo: di "
                    f"«{preferred_name}», nunca «el {animal.name}» ni "
                    f"«la {animal.name}»."
                ),
                (
                    "Regla: es un animal; no puede ser usuario, interlocutor "
                    "ni hablar con Atlas. Tampoco tiene proyectos, trabajo, "
                    "estudios, hobbies, planes o ilusiones humanas. Solo describe "
                    "datos y anécdotas reales registradas."
                ),
            ]
            lines.extend(
                self._build_speaker_relationship_context(
                    animal,
                    "animal",
                )
            )

            if animal.summary:
                lines.append(
                    f"Resumen verificado: {animal.summary}"
                )

            sections.append("\n".join(lines))
            matched_entities.append(("animal", animal))

        if len(matched_entities) >= 2:
            pair_lines = ["RELACIONES ENTRE LAS ENTIDADES MENCIONADAS"]
            for index, (source_type, source) in enumerate(matched_entities):
                for target_type, target in matched_entities[index + 1:]:
                    forward = (
                        self.relationship_engine
                        .describe_relationship_between_entities(
                            source_entity_id=source.id,
                            source_entity_type=source_type,
                            target_entity_id=target.id,
                            target_entity_type=target_type,
                        )
                    )
                    reverse = (
                        self.relationship_engine
                        .describe_relationship_between_entities(
                            source_entity_id=target.id,
                            source_entity_type=target_type,
                            target_entity_id=source.id,
                            target_entity_type=source_type,
                        )
                    )
                    if forward:
                        pair_lines.append(f"- {forward}")
                    if reverse and reverse != forward:
                        pair_lines.append(f"- {reverse}")
            if len(pair_lines) > 1:
                sections.append("\n".join(pair_lines))

        if not sections:
            return ""

        return (
            "ENTIDADES MENCIONADAS EN EL MENSAJE\n\n"
            + "\n\n".join(sections)
            + "\n\n"
            "Estas entidades son el tema de la pregunta. "
            "No las confundas con la persona que está hablando. "
            "No inventes biografías, parentescos, domicilios, aficiones ni "
            "anécdotas que no estén escritos en este contexto. "
            "No hables como la entidad mencionada y no atribuyas sus "
            "relaciones al asistente."
        )

    @classmethod
    def _is_entity_or_relationship_query(
        cls,
        user_message: str,
    ) -> bool:
        """Detecta consultas factuales sobre personas, animales o parentescos."""

        normalized = cls._normalize_entity_text(user_message)
        query_markers = (
            "quien es ",
            "quien era ",
            "hablame de ",
            "cuentame sobre ",
            "que sabes de ",
            "madre de ",
            "padre de ",
            "hermana de ",
            "hermano de ",
            "tia de ",
            "tio de ",
            "abuela de ",
            "abuelo de ",
            "prima de ",
            "primo de ",
            "pareja de ",
            "novia de ",
            "novio de ",
            "hija de ",
            "hijo de ",
            "cunada de ",
            "cunado de ",
            "suegra de ",
            "suegro de ",
            "nuera de ",
            "yerno de ",
            "sobrina de ",
            "sobrino de ",
            "nieta de ",
            "nieto de ",
            "mascota de ",
            "animal de ",
        )
        return any(marker in normalized for marker in query_markers)

    @classmethod
    def _needs_conversation_continuity(
        cls,
        user_message: str,
    ) -> bool:
        """Indica si la consulta necesita realmente el turno anterior."""

        normalized = cls._normalize_entity_text(user_message)
        continuity_patterns = (
            r"^(?:y|entonces|ademas)\b",
            r"\b(?:el|ella|ellos|ellas)\b",
            r"\b(?:su|sus)\s+(?:madre|padre|hermana|hermano|tia|tio|pareja)\b",
            r"^(?:la|el)\s+(?:primera|primero|segunda|segundo|1|2)$",
            r"^(?:si|no|vale|correcto|esa|ese|esta|este)$",
        )
        return any(
            re.search(pattern, normalized)
            for pattern in continuity_patterns
        )

    def _build_scoped_conversation_context(
        self,
        context,
        user_message: str,
    ) -> str:
        """
        Construye un historial seguro para el prompt sin borrar la conversación.

        En preguntas familiares explícitas se omiten respuestas antiguas para
        impedir que una equivocación previa contamine la siguiente consulta.
        En seguimientos que dependen del contexto se conserva solo el último
        intercambio.
        """

        if not self._is_entity_or_relationship_query(user_message):
            return context.format_for_prompt()

        if not self._needs_conversation_continuity(user_message):
            return (
                "Consulta factual independiente. No uses respuestas anteriores "
                "para deducir nombres o relaciones; resuelve exclusivamente con "
                "las entidades y relaciones verificadas del prompt actual."
            )

        try:
            messages = context.get_messages()[-2:]
        except AttributeError:
            messages = []

        if not messages:
            return (
                "Seguimiento sin historial suficiente. Pide una aclaración si "
                "el referente no puede identificarse con seguridad."
            )

        labels = {
            "user": "Usuario",
            "assistant": "Asistente",
            "system": "Sistema",
        }
        formatted = [
            f"{labels.get(message.get('role'), 'Mensaje')}: "
            f"{message.get('content', '').strip()}"
            for message in messages
            if isinstance(message, dict) and message.get("content")
        ]
        return (
            "ÚLTIMO INTERCAMBIO RELEVANTE (solo para resolver pronombres o "
            "elipsis; no lo trates como fuente factual):\n\n"
            + "\n\n".join(formatted)
        )

    @staticmethod
    def _responses_are_too_similar(first: str, second: str) -> bool:
        """Detecta respuestas repetidas o casi calcadas."""

        clean_first = re.sub(r"\s+", " ", str(first).casefold()).strip()
        clean_second = re.sub(r"\s+", " ", str(second).casefold()).strip()
        if not clean_first or not clean_second:
            return False
        if clean_first == clean_second:
            return True
        return SequenceMatcher(None, clean_first, clean_second).ratio() >= 0.86

    def _recent_assistant_responses(self, context, limit: int = 4) -> list[str]:
        """Recupera respuestas recientes para evitar repeticiones literales."""

        try:
            messages = context.get_messages()
        except AttributeError:
            return []
        responses = [
            str(message.get("content", ""))
            for message in messages
            if isinstance(message, dict) and message.get("role") == "assistant"
        ]
        return responses[-limit:]

    @classmethod
    def _response_topic_key(
        cls,
        user_message: str,
        conversation_user: str,
    ) -> str:
        """Agrupa preguntas equivalentes para recordar sus últimas respuestas."""

        normalized = cls._normalize_entity_text(user_message)

        # Las consultas internas no deben compartir una clave vacía.
        # «quién eres» y «quién soy» tratan asuntos distintos aunque
        # ambas queden sin texto al retirar el prefijo.
        exact_topics = {
            "presentate": "identidad_asistente",
            "quien eres": "identidad_asistente",
            "quien soy": "identidad_interlocutor",
        }
        if normalized in exact_topics:
            normalized = exact_topics[normalized]
        else:
            prefixes = (
                "quien es ",
                "quien era ",
                "hablame de ",
                "cuentame sobre ",
                "cuentame quien es ",
                "dime quien es ",
                "que sabes de ",
            )
            for prefix in prefixes:
                if normalized.startswith(prefix):
                    normalized = normalized[len(prefix):].strip()
                    break

        normalized = re.sub(
            r"\b(?:por favor|otra vez|de nuevo|un poco|algo)\b",
            " ",
            normalized,
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return f"{cls._normalize_entity_text(conversation_user)}:{normalized}"

    def _generate_varied_response(
        self,
        prompt: str,
        context,
        user_message: str,
        conversation_user: str,
    ) -> str:
        """Evita repetir respuestas recientes o respuestas del mismo tema."""

        recent = self._recent_assistant_responses(context)
        history = getattr(self, "_response_history_by_topic", None)
        if not isinstance(history, dict):
            history = {}
            self._response_history_by_topic = history

        topic_key = self._response_topic_key(
            user_message,
            conversation_user,
        )
        topic_history = list(history.get(topic_key, []))[-4:]
        forbidden = [*recent, *topic_history]

        response = self.ai_provider.generate(prompt)

        def is_repeated(candidate: str) -> bool:
            return any(
                self._responses_are_too_similar(candidate, previous)
                for previous in forbidden
                if previous
            )

        if is_repeated(response):
            avoided_text = "\n\n---\n\n".join(
                [*topic_history[-2:], response]
            )
            variation_prompt = (
                prompt
                + "\n\nREGLA EXTRA DE VARIACIÓN PARA ESTA RESPUESTA:\n"
                + "La redacción resultó demasiado parecida a respuestas "
                  "anteriores sobre el mismo asunto. Conserva exactamente los "
                  "mismos hechos verificables, pero cambia claramente el inicio, "
                  "la estructura, el orden de las ideas, los conectores, el tono "
                  "y el cierre. No copies frases completas ni añadas datos.\n"
                + f"Redacciones que debes evitar:\n{avoided_text}"
            )
            alternative = self.ai_provider.generate(variation_prompt)
            if alternative.strip() and not is_repeated(alternative):
                response = alternative

        history.setdefault(topic_key, []).append(response)
        history[topic_key] = history[topic_key][-5:]
        return response

    def _handle_ai(
        self,
        original_text: str,
    ) -> bool:
        """
        Intenta responder mediante la inteligencia artificial local.

        Devuelve:
            True:
                La entrada fue gestionada por la capa de IA.

            False:
                La IA está desactivada o no está disponible.
        """

        original_text, clarification_handled = (
            self._prepare_entity_clarification(
                original_text
            )
        )

        if clarification_handled:
            return True

        verified_response = self._answer_verified_entity_query(
            original_text
        )
        if verified_response is not None:
            normalized_verified_query = self._normalize_entity_text(original_text)
            response_kind = (
                "biography"
                if any(marker in normalized_verified_query for marker in (
                    "quien es", "quien era", "hablame de",
                    "cuentame sobre", "que sabes de",
                    "donde vive", "donde nacio", "cuando nacio",
                    "en que trabaja", "donde trabaja",
                ))
                else "relationship"
            )
            verified_response = self._style_verified_response(
                verified_response,
                response_kind=response_kind,
            )
            print()
            print(verified_response)
            try:
                direct_context = self._get_ai_context_for_user(
                    self._get_current_conversation_user()
                )
                direct_context.add_message(
                    role="user",
                    content=original_text,
                )
                direct_context.add_message(
                    role="assistant",
                    content=verified_response,
                )
            except (AttributeError, TypeError):
                pass
            self._resolved_entity_id = None
            self._resolved_entity_candidate_ids = set()
            return True

        if not self.can_use_ai():
            return False

        if self.ai_provider is None:

            info(
                "IA no disponible: "
                "no existe ningún proveedor configurado."
            )

            return False

        if not self.ai_provider.is_available():

            info(
                "IA no disponible: "
                "el proveedor no responde."
            )

            return False

        # ---------------------------------------------------------------------
        # INTERLOCUTOR ACTUAL
        # ---------------------------------------------------------------------

        conversation_user = (
            self._get_current_conversation_user()
        )

        # La identidad del asistente pertenece al usuario autenticado,
        # no a una persona mencionada ni a un interlocutor invitado.
        identity_preference_user = self.get_user()

        if (
            self.identity_manager.get_current_user()
            != identity_preference_user
        ):

            self.identity_manager.load_user(
                identity_preference_user
            )

        # ---------------------------------------------------------------------
        # CONTEXTO TEMPORAL DE LA CONVERSACIÓN
        # ---------------------------------------------------------------------

        current_ai_context = (
            self._get_ai_context_for_user(
                conversation_user
            )
        )

        conversation_context = (
            self._build_scoped_conversation_context(
                current_ai_context,
                original_text,
            )
        )

        # ---------------------------------------------------------------------
        # INFORMACIÓN REAL DEL SISTEMA
        # ---------------------------------------------------------------------

        current_system_info = get_system_info()

        system_information = format_system_info_for_ai(
            current_system_info
        )

        # ---------------------------------------------------------------------
        # MEMORIA PERSISTENTE RELEVANTE
        # ---------------------------------------------------------------------

        # El propietario de los recuerdos sigue siendo
        # el usuario autenticado de la sesión.
        memory_owner = self.get_user()

        # La persona que consulta los recuerdos es siempre
        # el interlocutor actual.
        memory_viewer = (
            self.conversation_identity
            .get_memory_viewer()
        )

        if memory_viewer is None:

            memory_viewer = conversation_user

        viewer_profile = (
            self.users.get_profile(
                memory_viewer
            )
        )

        relevant_memories = (
            self.memory_retriever.find(
                query=original_text,
                owner=memory_owner,
                viewer=memory_viewer,
                viewer_profile=viewer_profile,
                limit=5,
            )
        )

        relevant_memories_text = (
            self.memory_retriever.format_for_prompt(
                relevant_memories
            )
        )

        if relevant_memories:

            info(
                f"Recuerdos añadidos al prompt de IA. "
                f"Propietario: {memory_owner}. "
                f"Consultante: {memory_viewer}. "
                f"Cantidad: {len(relevant_memories)}."
            )

        # ---------------------------------------------------------------------
        # IDENTIDAD DE LA PERSONA QUE HABLA
        # ---------------------------------------------------------------------

        conversation_identity_context = (
            self.conversation_identity
            .build_prompt_context()
        )

        # ---------------------------------------------------------------------
        # IDENTIDAD DEL ASISTENTE
        # ---------------------------------------------------------------------

        assistant_identity_context = (
            self.identity_manager
            .build_prompt_context()
        )

        active_assistant_name = (
            self.identity_manager
            .get_active_display_name()
        )

        referenced_entities_context = (
            self._build_referenced_entities_context(
                original_text
            )
        )

        # La selección solo se aplica a esta respuesta de seguimiento.
        self._resolved_entity_id = None
        self._resolved_entity_candidate_ids = set()

        # Ambos contextos se mantienen separados para que
        # el modelo no confunda al interlocutor con el asistente.
        identity_sections = [
                (
                    "IDENTIDAD DE LA PERSONA "
                    "QUE ESTÁ HABLANDO\n\n"
                    f"{conversation_identity_context}"
                ),
            (
                "IDENTIDAD Y PERSONALIDAD "
                "DEL ASISTENTE\n\n"
                f"{assistant_identity_context}"
            ),
        ]

        if referenced_entities_context:
            identity_sections.append(
                referenced_entities_context
            )

        identity_context = "\n\n".join(
            identity_sections
        )

        # ---------------------------------------------------------------------
        # CONSTRUCCIÓN DEL PROMPT
        # ---------------------------------------------------------------------

        prompt = self.prompt_builder.build(
            user_message=original_text,
            user_name=conversation_user,
            project_name=self.get_project(),
            assistant_name=active_assistant_name,
            atlas_version=self.get_version(),
            capabilities=self.get_capabilities(),
            system_information=system_information,
            identity_context=identity_context,
            relevant_memories=relevant_memories_text,
            conversation_context=conversation_context,
        )

        try:

            response = self._generate_varied_response(
                prompt,
                current_ai_context,
                original_text,
                conversation_user,
            )

        except (
            RuntimeError,
            ValueError,
        ) as exception:

            info(
                f"Error de IA: {exception}"
            )

            print()
            print(
                "No he podido consultar la inteligencia "
                "artificial local."
            )

            return True

        current_ai_context.add_message(
            role="user",
            content=original_text,
        )

        current_ai_context.add_message(
            role="assistant",
            content=response,
        )

        info(
            f"Respuesta generada por IA local. "
            f"Proveedor: "
            f"{self.ai_provider.get_provider_name()}. "
            f"Modelo: "
            f"{self.ai_provider.get_model_name()}."
        )

        print()
        print(response)

        return True

    def clear_ai_context(
        self,
    ) -> None:
        """
        Elimina el contexto temporal de la persona
        que está hablando actualmente.
        """

        current_conversation_user = (
            self._get_current_conversation_user()
        )

        current_context = (
            self._get_ai_context_for_user(
                current_conversation_user
            )
        )

        current_context.clear()

        info(
            f"Contexto temporal de IA eliminado "
            f"para {current_conversation_user}."
        )

    def clear_ai_context_for_user(
        self,
        user: str,
    ) -> bool:
        """
        Elimina el contexto temporal de un usuario.

        El propio usuario puede borrar su contexto.
        El propietario del sistema puede borrar cualquiera.
        """

        current_user = (
            self._get_current_conversation_user()
        )

        same_user = (
            self._normalize_ai_context_user(
                current_user
            )
            == self._normalize_ai_context_user(
                user
            )
        )

        if (
            not same_user
            and not self.can_manage_user_contexts()
        ):

            info(
                f"Intento no autorizado de eliminar "
                f"el contexto de {user}. "
                f"Solicitante: {current_user}."
            )

            return False

        context_key = self._normalize_ai_context_user(
            user
        )

        user_context = self.ai_contexts.get(
            context_key
        )

        if user_context is not None:
            user_context.clear()

        info(
            f"Contexto temporal de IA eliminado. "
            f"Solicitante: {current_user}. "
            f"Propietario: {user}."
        )

        return True

    def get_ai_context_size(
        self,
    ) -> int:
        """
        Devuelve la cantidad de mensajes del interlocutor actual.
        """

        return (
            self.get_current_ai_context()
            .count_messages()
        )

    def get_ai_context_size_for_user(
        self,
        user: str,
    ) -> int:
        """
        Devuelve la cantidad de mensajes de un usuario.
        """

        return (
            self._get_ai_context_for_user(
                user
            ).count_messages()
        )

    def get_ai_context_users(
        self,
    ) -> list[str]:
        """
        Devuelve las claves de interlocutores con contexto creado.
        """

        return sorted(
            self.ai_contexts.keys()
        )

    def can_manage_user_contexts(
        self,
    ) -> bool:
        """
        Indica si la persona que está hablando puede
        administrar contextos de otros usuarios.

        Los permisos pertenecen al interlocutor real,
        no al usuario autenticado de la sesión.
        """

        conversation_identity = getattr(
            self,
            "conversation_identity",
            None,
        )

        permission_viewer = None

        if conversation_identity is not None:
            permission_viewer = (
                conversation_identity
                .get_permission_viewer()
            )

        if permission_viewer is None:
            permission_viewer = self.get_user()

        current_profile = self.users.get_profile(
            permission_viewer
        )

        return "owner" in current_profile.get(
            "roles",
            [],
        )

    def get_ai_context_messages_for_user(
        self,
        user: str,
    ) -> list[dict[str, str]] | None:
        """
        Devuelve una copia del contexto de un usuario.

        Devuelve None cuando no existe autorización.
        """

        current_user = (
            self._get_current_conversation_user()
        )

        same_user = (
            self._normalize_ai_context_user(
                current_user
            )
            == self._normalize_ai_context_user(
                user
            )
        )

        if (
            not same_user
            and not self.can_manage_user_contexts()
        ):

            info(
                f"Acceso denegado al contexto de {user}. "
                f"Solicitante: {current_user}."
            )

            return None

        context_key = self._normalize_ai_context_user(
            user
        )

        user_context = self.ai_contexts.get(
            context_key
        )

        if user_context is None:
            return []

        info(
            f"Contexto de IA consultado. "
            f"Solicitante: {current_user}. "
            f"Propietario: {user}."
        )

        return user_context.get_messages()

    def _format_context_messages(
        self,
        user: str,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Convierte una colección de mensajes en texto legible.

        Este formato se utiliza internamente para enviar
        una conversación al modelo y generar un resumen.
        """

        assistant_name = (
            self.identity_manager
            .get_active_display_name()
        )

        role_labels = {
            "user": user,
            "assistant": assistant_name,
            "system": "Sistema",
        }

        formatted_messages = []

        for message in messages:

            role = message.get(
                "role",
                "unknown",
            )

            content = message.get(
                "content",
                "",
            ).strip()

            if not content:
                continue

            label = role_labels.get(
                role,
                role,
            )

            formatted_messages.append(
                f"{label}: {content}"
            )

        return "\n\n".join(
            formatted_messages
        )

    def format_ai_context_for_user(
        self,
        user: str,
    ) -> str | None:
        """
        Devuelve el contexto completo de un usuario
        en formato legible.

        Este método conserva el historial literal y puede utilizarse
        para tareas administrativas o de depuración.
        """

        messages = (
            self.get_ai_context_messages_for_user(
                user
            )
        )

        if messages is None:
            return None

        if not messages:
            return ""

        return self._format_context_messages(
            user=user,
            messages=messages,
        )

    def _build_context_summary_cache_key(
        self,
        user: str,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Crea una clave única para el resumen de una conversación.

        La clave cambia automáticamente cuando:

        - Se añaden mensajes.
        - Se modifica el contenido.
        - Se cambia de modelo.
        """

        serialized_messages = json.dumps(
            messages,
            ensure_ascii=False,
            sort_keys=True,
        )

        context_hash = hashlib.sha256(
            serialized_messages.encode(
                "utf-8"
            )
        ).hexdigest()

        model_name = (
            self.ai_provider.get_model_name()
            if self.ai_provider is not None
            else "no-provider"
        )

        normalized_user = (
            self._normalize_ai_context_user(
                user
            )
        )

        assistant_identity_name = (
            self.identity_manager
            .get_active_identity_name()
        )

        return (
            f"context-summary:"
            f"{normalized_user}:"
            f"{assistant_identity_name}:"
            f"{model_name}:"
            f"{context_hash}"
        )

    def summarize_ai_context_for_user(
        self,
        user: str,
    ) -> str | None:
        """
        Genera un resumen natural de la conversación
        mantenida con un usuario.

        El resumen indica:

        - Qué preguntó el usuario.
        - Qué se le respondió.
        - Si pidió realizar alguna acción.
        - Si quedó algo pendiente.

        No devuelve una copia literal del historial.
        """

        messages = (
            self.get_ai_context_messages_for_user(
                user
            )
        )

        if messages is None:
            return None

        if not messages:
            return ""

        if (
            self.ai_provider is None
            or not self.ai_provider.is_available()
        ):

            info(
                f"No se pudo resumir el contexto de {user}: "
                "el proveedor de IA no está disponible."
            )

            return (
                f"{user} mantuvo una conversación conmigo, "
                "pero ahora mismo no puedo preparar un resumen "
                "fiable porque la inteligencia artificial local "
                "no está disponible."
            )

        cache_key = (
            self._build_context_summary_cache_key(
                user=user,
                messages=messages,
            )
        )

        cached_summary = self.ai_cache.get(
            cache_key
        )

        if cached_summary is not None:

            info(
                f"Resumen de contexto recuperado "
                f"desde caché para {user}."
            )

            return cached_summary

        summary = (
            self._format_context_messages(
                user=user,
                messages=messages,
            )
        )

        active_assistant_name = (
            self.identity_manager
            .get_active_display_name()
        )

        summary_prompt = (
            f"Eres {active_assistant_name}, una identidad "
            f"del asistente del Proyecto Atlas.\n\n"

            f"Resume brevemente la conversación que mantuviste "
            f"con {user}.\n\n"

            "Debes explicar de forma natural:\n"
            "- Qué te preguntó o pidió.\n"
            "- Qué le respondiste.\n"
            "- Si realizaste alguna acción.\n"
            "- Si quedó algo pendiente.\n\n"

            "No copies literalmente toda la conversación.\n"
            "No inventes información.\n"
            "No añadas detalles que no aparezcan en el historial.\n"

            f"Habla en primera persona como "
            f"{active_assistant_name}.\n"

            "Utiliza uno o dos párrafos breves.\n\n"

            "CONVERSACIÓN:\n\n"

            f"{summary}"
        )

        try:

            summary = self.ai_provider.generate(
                summary_prompt
            ).strip()

        except (
            RuntimeError,
            ValueError,
        ) as exception:

            info(
                f"No se pudo resumir el contexto "
                f"de {user}: {exception}"
            )

            return (
                f"{user} mantuvo una conversación conmigo, "
                "pero ahora mismo no he podido preparar "
                "un resumen fiable."
            )

        self.ai_cache.set(
            key=cache_key,
            value=summary,
            ttl_seconds=600,
        )

        info(
            f"Resumen de contexto almacenado "
            f"en caché para {user}."
        )

        return summary
