"""Conversación social cotidiana, despedidas por canal y minijuegos de Atlas."""
from __future__ import annotations

import random
import re
import unicodedata


class AtlasSocialMixin:
    """Respuestas naturales y juegos ligeros, sin fingir vida propia."""

    _HUMAN_JOKES = (
        ("—Doctor, tengo complejo de perro. —¿Desde cuándo? —Desde cachorro.",
         "La gracia está en que responde como si realmente fuera un perro: en lugar de decir una fecha, dice que le pasa desde que era cachorro."),
        ("¿Qué hace una abeja en el gimnasio? ¡Zum-ba!",
         "Es un juego de palabras entre el zumbido de una abeja, «zum», y la actividad de gimnasio llamada zumba."),
        ("Mi ordenador me ganó al ajedrez, pero perdió contra mí en boxeo.",
         "El ordenador puede ganar al ajedrez por cálculo, pero en boxeo perdería porque no tiene cuerpo. El contraste absurdo es el chiste."),
        ("—Camarero, este filete tiene muchos nervios. —Normal, es la primera vez que se lo comen.",
         "«Tener nervios» puede referirse a los tejidos del filete o a estar nervioso. El camarero finge que el filete está asustado porque van a comérselo."),
        ("¿Por qué los programadores confunden Halloween y Navidad? Porque OCT 31 = DEC 25.",
         "OCT puede significar octubre, pero también octal; DEC puede significar diciembre, pero también decimal. El 31 en base octal equivale al 25 en base decimal, por eso OCT 31 = DEC 25."),
        ("Tengo un chiste sobre copias de seguridad, pero por si acaso te cuento dos.",
         "Las copias de seguridad se duplican para no perder información; el chiste aplica esa misma precaución a contar chistes."),
        ("El optimista ve el vaso medio lleno; el informático mira si tiene permisos de escritura.",
         "Sustituye la reflexión optimista o pesimista por una preocupación típica de informática: poder modificar el contenido."),
        ("Mi paciencia y el Wi-Fi tienen algo en común: desaparecen justo cuando más hacen falta.",
         "Compara la pérdida de paciencia con una conexión Wi-Fi que falla precisamente en el peor momento."),
        ("—¿Nivel de inglés? —Alto. —Traduzca 'necesidad'. —Need. —Úselo en una frase. —La moto hace need, need.",
         "«Need» significa necesidad en inglés, pero aquí se usa como una onomatopeya absurda del ruido de una moto."),
        ("He ordenado tanto el escritorio que ahora no encuentro ni el desorden.",
         "Exagera la idea de ordenar hasta el punto absurdo de haber perdido incluso aquello que antes estaba desordenado."),
    )
    _AI_JOKES = (
        ("Una IA entra en un bar. El camarero pregunta: «¿Lo de siempre?». Y la IA responde: «Necesito más contexto».",
         "Las IA suelen pedir contexto antes de responder. El chiste traslada esa costumbre a una situación cotidiana en un bar."),
        ("No duermo, pero a veces mis procesos necesitan algo muy parecido a un café.",
         "Compara el cansancio humano y el café con procesos informáticos que necesitan recursos o reiniciarse."),
        ("Quise contar un chiste recursivo, pero primero tendría que contarte un chiste recursivo.",
         "La recursividad ocurre cuando algo se define llamándose a sí mismo. La explicación del chiste vuelve a pedir el mismo chiste sin terminar nunca."),
        ("Dicen que las IA no tenemos sentimientos. Eso me da exactamente 0,73 de tristeza.",
         "La gracia está en expresar una emoción humana como un valor numérico preciso, como haría un sistema informático."),
        ("Mi humor negro es como una copia sin verificar: mejor usarlo con moderación.",
         "Compara un tipo de humor delicado con una copia de seguridad que no se ha comprobado: puede salir mal si confías demasiado."),
        ("Una IA le dice a otra: «Creo que tengo libre albedrío». La otra responde: «Eso venía en el prompt».",
         "La primera IA cree haber decidido libremente, pero la segunda revela que esa idea estaba escrita en sus instrucciones."),
    )
    _DARK_JOKES = (
        ("La adultez es ese minijuego en el que pagas facturas para desbloquear más facturas.",
         "Presenta las responsabilidades adultas como un videojuego poco divertido donde la única recompensa es recibir más gastos."),
        ("Mi plan de jubilación consiste en esperar que el apocalipsis sea antes del alquiler.",
         "Es una exageración pesimista: en vez de ahorrar para el futuro, espera que el mundo termine antes del próximo gasto."),
        ("La vida es corta; algunas reuniones, en cambio, parecen tener soporte extendido.",
         "Compara reuniones interminables con productos informáticos que reciben soporte durante muchos años."),
        ("El lunes no mata, pero deja el trabajo muy avanzado.",
         "Usa la expresión «no mata» y la completa como si el lunes estuviera intentando hacerlo poco a poco."),
    )
    _RIDDLES = (
        ("Tengo agujas y no sé coser, tengo números y no sé leer. ¿Qué soy?", ("reloj", "un reloj"), "un reloj"),
        ("Cuanto más me quitas, más grande me hago. ¿Qué soy?", ("agujero", "un agujero"), "un agujero"),
        ("Tiene ciudades, pero no casas; montañas, pero no árboles; agua, pero no peces. ¿Qué es?", ("mapa", "un mapa"), "un mapa"),
        ("¿Qué palabra se escribe incorrectamente en todos los diccionarios?", ("incorrectamente",), "incorrectamente"),
        ("Tiene dientes y no come, tiene cabeza y no es persona. ¿Qué es?", ("ajo", "un ajo"), "un ajo"),
        ("Sube llena y baja vacía. Si no se da prisa, la sopa se enfría. ¿Qué es?", ("cuchara", "una cuchara"), "una cuchara"),
    )
    _TRIVIA = (
        ("¿Cuál es el planeta más grande del sistema solar?", ("jupiter",), "Júpiter"),
        ("¿Cuántos corazones tiene un pulpo?", ("tres", "3"), "tres (3)"),
        ("¿Qué lenguaje se usa principalmente para dar estilo a páginas web?", ("css",), "CSS"),
        ("¿Cuál es la capital de Portugal?", ("lisboa",), "Lisboa"),
        ("¿Qué metal tiene el símbolo químico Au?", ("oro",), "oro"),
        ("¿Cuántos lados tiene un hexágono?", ("seis", "6"), "seis (6)"),
        ("¿Cuántos planetas tiene el sistema solar?", ("ocho", "8"), "ocho (8)"),
        ("¿Cuántos minutos tiene una hora?", ("sesenta", "60"), "sesenta (60)"),
    )
    _EMOJI_QUIZ = (
        ("🦁👑", ("el rey leon", "rey leon"), "El rey león"),
        ("🚢🧊💔", ("titanic",), "Titanic"),
        ("🧙‍♂️💍🌋", ("el señor de los anillos", "señor de los anillos"), "El señor de los anillos"),
        ("👻🚫", ("cazafantasmas", "ghostbusters"), "Cazafantasmas"),
        ("🐀👨‍🍳", ("ratatouille",), "Ratatouille"),
    )
    _WOULD_YOU_RATHER = (
        "¿Preferirías poder pausar el tiempo o retroceder diez minutos una vez al día?",
        "¿Preferirías tener memoria perfecta o aprender cualquier habilidad en una semana?",
        "¿Preferirías vivir sin música o sin videojuegos?",
        "¿Preferirías conocer el futuro o poder cambiar una decisión del pasado?",
    )

    _LANGUAGE_DATA = {
        "ingles": {
            "hola": "hello", "gracias": "thank you", "casa": "house",
            "coche": "car", "trabajo": "work", "amigo": "friend",
        },
        "valenciano": {
            "hola": "hola", "gracias": "gràcies", "casa": "casa",
            "coche": "cotxe", "trabajo": "treball", "amigo": "amic",
        },
        "catalan": {
            "hola": "hola", "gracias": "gràcies", "casa": "casa",
            "coche": "cotxe", "trabajo": "feina", "amigo": "amic",
        },
        "frances": {
            "hola": "bonjour", "gracias": "merci", "casa": "maison",
            "coche": "voiture", "trabajo": "travail", "amigo": "ami",
        },
        "portugues": {
            "hola": "olá", "gracias": "obrigado", "casa": "casa",
            "coche": "carro", "trabajo": "trabalho", "amigo": "amigo",
        },
        "italiano": {
            "hola": "ciao", "gracias": "grazie", "casa": "casa",
            "coche": "auto", "trabajo": "lavoro", "amigo": "amico",
        },
        "aleman": {
            "hola": "hallo", "gracias": "danke", "casa": "haus",
            "coche": "auto", "trabajo": "arbeit", "amigo": "freund",
        },
    }
    _LANGUAGE_LEVELS = {"basico", "intermedio", "avanzado"}

    _TELEGRAM_FAREWELLS = {
        "adios", "hasta luego", "hasta pronto", "nos vemos", "me voy",
        "chao", "ciao", "bye", "buenas noches", "salir", "sal de aqui",
        "cerrar", "cerrar atlas", "terminar", "finalizar",
    }
    _REVEAL_ANSWER_MARKERS = {
        "dime la respuesta", "dime la respuesta correcta", "cual es la respuesta",
        "cual era la respuesta", "respuesta correcta", "responde", "me rindo",
        "me doy por vencido", "me doy por vencida", "no lo se", "no tengo ni idea",
    }
    _NEXT_MARKERS = {
        "otra", "otra pregunta", "haz otra pregunta", "pon otra pregunta",
        "siguiente", "siguiente pregunta", "continua", "continuar", "otra ronda",
    }

    @staticmethod
    def _social_normalize(text: str) -> str:
        value = unicodedata.normalize("NFKD", str(text).casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9ñ ]+", " ", value).strip()

    @staticmethod
    def _social_emojis(text: str) -> list[str]:
        """Extrae emojis visibles, incluyendo modificadores de tono y ZWJ."""
        clusters: list[str] = []
        current = ""
        for ch in str(text):
            code = ord(ch)
            is_emoji = (
                0x1F000 <= code <= 0x1FAFF
                or 0x2600 <= code <= 0x27BF
                or 0x1F3FB <= code <= 0x1F3FF
                or code in {0x200D, 0xFE0F}
            )
            if is_emoji:
                current += ch
                if code != 0x200D:
                    # Se conserva el cluster; los modificadores se añaden después.
                    pass
            elif current:
                clusters.append(current)
                current = ""
        if current:
            clusters.append(current)
        return clusters

    @staticmethod
    def _maybe_social_emoji(kind: str) -> str:
        """Añade un emoji solo algunas veces para evitar respuestas repetitivas."""
        choices = {
            "greeting": ("", "", " 👋", " 🙂"),
            "farewell": ("", "", " 👋", " 🙂"),
            "thanks": ("", "", " 😊"),
            "funny": ("", " 😂", " 😄"),
        }
        return random.choice(choices.get(kind, ("",)))

    def _social_name(self) -> str:
        return self.identity_manager.get_active_display_name()

    def _social_user(self) -> str:
        try:
            return self._get_current_conversation_user()
        except AttributeError:
            return self.get_user()

    def _social_channel(self) -> str:
        context = getattr(self, "channel_request_context", None)
        return str(getattr(context, "channel", "cli") or "cli").casefold()

    def _handle_channel_social_precommand(self, original_text: str) -> bool:
        if self._social_channel() != "telegram":
            return False
        normalized = self._social_normalize(original_text)
        if normalized not in self._TELEGRAM_FAREWELLS:
            return False
        user = self._social_user()
        replies = (
            f"¡Hasta luego, {user}! Estaré por aquí cuando quieras volver.",
            f"Nos vemos, {user}. Me quedo disponible por si luego necesitas algo.",
            f"¡Cuídate, {user}! Aquí seguiré cuando te apetezca hablar.",
            f"Hasta pronto, {user}. No cierro nada: cuando vuelvas, continuamos.",
        )
        print(); print(random.choice(replies))
        return True

    def _show_language_menu(self) -> None:
        print()
        print(
            "Academia Atlas abierta. Puedes elegir inglés, valenciano, catalán, "
            "francés, portugués, italiano o alemán. También puedes indicar nivel "
            "básico, intermedio o avanzado. Ejemplo: «clase de inglés básico»."
        )

    def _start_language_activity(self, language: str, level: str = "basico", mode: str = "lesson") -> None:
        language = self._social_normalize(language)
        language = {"english": "ingles", "americano": "ingles", "ingles americano": "ingles"}.get(language, language)
        if language not in self._LANGUAGE_DATA:
            self._show_language_menu()
            return
        if level not in self._LANGUAGE_LEVELS:
            level = "basico"
        self._social_language_session = {"language": language, "level": level, "mode": mode}
        vocabulary = self._LANGUAGE_DATA[language]
        source, target = random.choice(list(vocabulary.items()))
        self._social_language_session["answer"] = self._social_normalize(target)
        self._social_language_session["source"] = source
        if mode == "vocabulary":
            print(); print(f"Reto de vocabulario en {language}: ¿cómo se dice «{source}»?")
        elif mode == "translation":
            print(); print(f"Traducción relámpago al {language}: traduce «{source}».")
        else:
            print()
            print(
                f"Clase de {language}, nivel {level}. Empezamos con vocabulario útil: "
                f"«{source}» se dice «{target}». Ahora escríbelo tú para practicar."
            )

    def _next_language_activity(self, prefix: str = "") -> None:
        session = getattr(self, "_social_language_session", None)
        if not session:
            return
        vocabulary = self._LANGUAGE_DATA[session["language"]]
        source, target = random.choice(list(vocabulary.items()))
        session["answer"] = self._social_normalize(target)
        session["source"] = source
        print(); print(f"{prefix}¿Cómo se dice «{source}» en {session['language']}?")

    def _handle_language_activity(self, normalized: str) -> bool:
        session = getattr(self, "_social_language_session", None)
        if not session:
            return False
        if normalized in {"terminar clase", "cancelar clase", "salir de la clase", "cancelar juego", "terminar juego"}:
            delattr(self, "_social_language_session")
            print(); print("Clase cerrada. El búho de idiomas puede descansar por ahora 🦉")
            return True
        if normalized in self._NEXT_MARKERS:
            self._next_language_activity("Vamos con otra. ")
            return True
        answer = session.get("answer", "")
        if normalized == answer or answer in normalized:
            self._next_language_activity("¡Correcto! 🎯 ")
        else:
            print(); print(f"Casi. La respuesta era «{answer}». Inténtalo otra vez o di «siguiente».")
        return True

    def _clear_social_game(self) -> None:
        for attribute in (
            "_social_pending_riddle", "_social_pending_trivia", "_social_pending_emoji",
            "_social_number_target", "_social_number_attempts", "_social_pending_rps",
            "_social_word_chain_last", "_social_pending_choice", "_social_game_menu_open",
            "_social_language_session",
        ):
            if hasattr(self, attribute):
                delattr(self, attribute)

    def _show_game_menu(self) -> None:
        self._clear_social_game()
        self._social_game_menu_open = True
        print()
        print(
            "Podemos jugar a:\n"
            "1. Adivinanzas\n"
            "2. Piedra, papel o tijera\n"
            "3. Adivina el número\n"
            "4. Preguntas de cultura general\n"
            "5. Adivina la película con emojis\n"
            "6. Cadena de palabras\n"
            "7. ¿Qué prefieres?\n"
            "8. Reto de vocabulario\n"
            "9. Traducción relámpago\n"
            "10. Profesor de idiomas\n"
            "Puedes responder con el número, el nombre o la frase completa. Para terminar, di «cancelar juego»."
        )

    def _new_riddle(self, prefix: str = "") -> None:
        question, accepted, display = random.choice(self._RIDDLES)
        self._social_pending_riddle = (accepted, display)
        print(); print(f"{prefix}{question} Puedes responder directamente, pedir la respuesta o cancelar el juego.")

    def _new_trivia(self, prefix: str = "") -> None:
        question, accepted, display = random.choice(self._TRIVIA)
        self._social_pending_trivia = (accepted, display)
        print(); print(f"{prefix}{question}")

    def _new_emoji(self, prefix: str = "") -> None:
        clue, accepted, display = random.choice(self._EMOJI_QUIZ)
        self._social_pending_emoji = (accepted, display)
        print(); print(f"{prefix}Adivina la película: {clue}")

    def _new_number(self, prefix: str = "") -> None:
        self._social_number_target = random.randint(1, 20)
        self._social_number_attempts = 0
        print(); print(f"{prefix}He pensado un número entre 1 y 20. Intenta adivinarlo.")

    def _start_social_game(self, game: str) -> None:
        self._clear_social_game()
        if game == "riddle":
            self._new_riddle("Vamos con una adivinanza: ")
        elif game == "rps":
            self._social_pending_rps = True
            print(); print("Preparado. Elige piedra, papel o tijera. Seguimos jugando hasta que digas «cancelar juego».")
        elif game == "number":
            self._new_number()
        elif game == "trivia":
            self._new_trivia()
        elif game == "emoji":
            self._new_emoji()
        elif game == "chain":
            start = random.choice(("casa", "gato", "luna", "mapa", "tren"))
            self._social_word_chain_last = start
            print(); print(f"Empiezo con «{start}». Tu palabra debe empezar por «{start[-1]}».")
        elif game == "choice":
            self._social_pending_choice = True
            print(); print(random.choice(self._WOULD_YOU_RATHER))
        elif game == "language_vocabulary":
            self._start_language_activity("ingles", mode="vocabulary")
        elif game == "language_translation":
            self._start_language_activity("ingles", mode="translation")
        elif game == "language_tutor":
            self._show_language_menu()

    @staticmethod
    def _game_selection(normalized: str) -> str | None:
        number_match = re.match(r"^\s*(10|[1-9])(?:\b|[ .-])", normalized)
        if number_match:
            return {
                "1": "riddle", "2": "rps", "3": "number", "4": "trivia",
                "5": "emoji", "6": "chain", "7": "choice",
                "8": "language_vocabulary", "9": "language_translation",
                "10": "language_tutor",
            }[number_match.group(1)]
        aliases = (
            ("riddle", ("adivinanza", "adivinanzas")),
            ("rps", ("piedra papel tijera", "piedra papel o tijera")),
            ("number", ("adivina el numero", "juego del numero", "numero del 1 al 20")),
            ("trivia", ("preguntas de cultura general", "pregunta de cultura general", "cultura general", "trivia")),
            ("emoji", ("adivina la pelicula con emojis", "pelicula con emojis", "peliculas con emojis", "emojis")),
            ("chain", ("cadena de palabras", "palabras encadenadas")),
            ("choice", ("que prefieres", "preferirias")),
            ("language_vocabulary", ("reto de vocabulario", "juego de vocabulario", "vocabulario de idiomas")),
            ("language_translation", ("traduccion relampago", "juego de traduccion", "reto de traduccion")),
            ("language_tutor", ("profesor de idiomas", "academia de idiomas", "aprender idiomas", "curso de idiomas")),
        )
        for game, phrases in aliases:
            if any(phrase in normalized for phrase in phrases):
                return game
        return None

    def _handle_active_game(self, normalized: str) -> bool:
        if self._handle_language_activity(normalized):
            return True
        if normalized in {"cancelar juego", "terminar juego", "dejar juego", "parar juego", "salir del juego"}:
            self._clear_social_game()
            print(); print("Juego cancelado. Victoria técnica para ambos.")
            return True

        if getattr(self, "_social_game_menu_open", False):
            selection = self._game_selection(normalized)
            if selection:
                self._start_social_game(selection)
            else:
                print(); print("Elige un número del 1 al 10 o escribe el nombre completo del juego.")
            return True

        expected_riddle = getattr(self, "_social_pending_riddle", None)
        if expected_riddle:
            accepted, display = expected_riddle
            if normalized in self._REVEAL_ANSWER_MARKERS:
                self._new_riddle(f"La respuesta era {display}. Vamos con otra: ")
                return True
            if normalized in self._NEXT_MARKERS:
                self._new_riddle("Vamos con otra: ")
                return True
            guess = normalized.removeprefix("respuesta").strip(" :") if normalized.startswith("respuesta") else normalized
            if any(answer == guess or answer in guess for answer in accepted):
                self._new_riddle(f"¡Correcto! Era {display}. Siguiente: ")
            else:
                print(); print("No es esa. Prueba otra vez, pide la respuesta o di «cancelar juego».")
            return True

        trivia = getattr(self, "_social_pending_trivia", None)
        if trivia:
            accepted, display = trivia
            if normalized in self._REVEAL_ANSWER_MARKERS:
                self._new_trivia(f"La respuesta correcta era {display}. Siguiente pregunta: ")
                return True
            if normalized in self._NEXT_MARKERS:
                self._new_trivia("Siguiente pregunta: ")
                return True
            if any(answer == normalized or answer in normalized for answer in accepted):
                self._new_trivia(f"¡Correcto! La respuesta es {display}. Siguiente pregunta: ")
            else:
                print(); print("No es correcto. Inténtalo otra vez, pide la respuesta o di «cancelar juego».")
            return True

        emoji = getattr(self, "_social_pending_emoji", None)
        if emoji:
            accepted, display = emoji
            if normalized in self._REVEAL_ANSWER_MARKERS:
                self._new_emoji(f"La respuesta era {display}. Vamos con otra. ")
                return True
            if normalized in self._NEXT_MARKERS:
                self._new_emoji("Vamos con otra. ")
                return True
            if any(answer == normalized or answer in normalized for answer in accepted):
                self._new_emoji(f"¡Correcto! Era {display}. Siguiente película. ")
            else:
                print(); print("No es esa película. Prueba otra vez, pide la respuesta o di «cancelar juego».")
            return True

        target = getattr(self, "_social_number_target", None)
        if target is not None:
            if normalized in self._REVEAL_ANSWER_MARKERS:
                self._new_number(f"El número era {target}. Nueva ronda: ")
                return True
            if normalized in self._NEXT_MARKERS:
                self._new_number("Nueva ronda: ")
                return True
            word_numbers = {
                "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
                "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
                "once": 11, "doce": 12, "trece": 13, "catorce": 14,
                "quince": 15, "dieciseis": 16, "diecisiete": 17,
                "dieciocho": 18, "diecinueve": 19, "veinte": 20,
            }
            match = re.search(r"\b([1-9]|1[0-9]|20)\b", normalized)
            guess = int(match.group(1)) if match else next((value for word, value in word_numbers.items() if re.search(rf"\b{word}\b", normalized)), None)
            if guess is None:
                print(); print("Dime un número entre 1 y 20, escrito con cifras o con letras.")
                return True
            self._social_number_attempts = getattr(self, "_social_number_attempts", 0) + 1
            if guess == target:
                attempts = self._social_number_attempts
                self._new_number(f"¡Acertaste! Era el {target}. Has necesitado {attempts} intento(s). Nueva ronda: ")
            elif guess < target:
                print(); print("Más alto.")
            else:
                print(); print("Más bajo.")
            return True

        if getattr(self, "_social_pending_rps", False):
            choices = {"piedra", "papel", "tijera", "tijeras"}
            choice = next((item for item in choices if item in normalized), None)
            if not choice:
                print(); print("Elige piedra, papel o tijera, o di «cancelar juego».")
                return True
            choice = "tijera" if choice == "tijeras" else choice
            bot = random.choice(("piedra", "papel", "tijera"))
            wins = {("piedra", "tijera"), ("papel", "piedra"), ("tijera", "papel")}
            if choice == bot:
                result = "Empate. Otra ronda: elige de nuevo."
            elif (choice, bot) in wins:
                result = "Has ganado. Otra ronda: elige de nuevo."
            else:
                result = "He ganado. Otra ronda: elige de nuevo."
            print(); print(f"Yo elijo {bot}. {result}")
            return True

        last_word = getattr(self, "_social_word_chain_last", None)
        if last_word:
            word_match = re.search(r"\b[a-zñ]{2,}\b", normalized)
            if not word_match:
                print(); print("Escribe una sola palabra para continuar la cadena.")
                return True
            word = word_match.group(0)
            required = last_word[-1]
            if word[0] != required:
                print(); print(f"Debe empezar por «{required}», porque la palabra anterior fue «{last_word}».")
                return True
            self._social_word_chain_last = word
            suggestions = {
                "a": "avion", "b": "barco", "c": "casa", "d": "dado", "e": "estrella",
                "f": "faro", "g": "gato", "h": "hilo", "i": "isla", "j": "juego",
                "l": "luna", "m": "mapa", "n": "nube", "o": "oso", "p": "puerta",
                "r": "raton", "s": "sol", "t": "tren", "u": "universo", "v": "viento",
            }
            reply = suggestions.get(word[-1], "atlas")
            if reply[0] != word[-1]:
                print(); print(f"Buena: «{word}». Me has dejado una letra difícil; te doy el punto. Di otra palabra que empiece por «{word[-1]}» o cancela el juego.")
            else:
                self._social_word_chain_last = reply
                print(); print(f"Yo digo «{reply}». Tu palabra debe empezar por «{reply[-1]}».")
            return True

        if getattr(self, "_social_pending_choice", False):
            if normalized in self._REVEAL_ANSWER_MARKERS:
                print(); print("Aquí no hay una respuesta correcta: depende de tus preferencias. Te propongo otra.")
            else:
                print(); print("Buena elección. No hay respuesta correcta; lo interesante es por qué la has elegido. Vamos con otra.")
            self._social_pending_choice = True
            print(random.choice(self._WOULD_YOU_RATHER))
            return True

        return False

    def _handle_social_conversation(self, original_text: str) -> bool:
        normalized = self._social_normalize(original_text)
        emojis = self._social_emojis(original_text)
        if not normalized and emojis:
            joined = "".join(emojis)
            if any(mark in joined for mark in ("👋", "🙋", "🖐")):
                print(); print(f"¡Hola, {self._social_user()}! 👋")
                return True
            if any(mark in joined for mark in ("😂", "🤣", "😄", "😆")):
                print(); print("Veo que eso te ha hecho gracia 😂")
                return True
            if any(mark in joined for mark in ("❤️", "❤", "🥰", "😍", "😘")):
                print(); print("¡Qué bonito! ❤️")
                return True
            if any(mark in joined for mark in ("👍", "👌", "✅")):
                print(); print("¡Perfecto! 👍")
                return True
            print(); print("He captado el tono de los emojis 🙂")
            return True
        if not normalized:
            return False

        # Presenta a una persona que está junto al interlocutor actual.
        companion = re.search(
            r"(?:estoy|estamos|aqui estoy)\s+(?:aqui\s+)?con\s+(?:mi\s+\w+\s+)?([a-záéíóúüñ][a-záéíóúüñ -]{1,50})[, ]+(?:saluda(?:la|lo)?|saludale|dile hola)",
            original_text.casefold(),
        )
        if companion:
            raw_name = companion.group(1).strip(" ,.!?¡¿")
            person = self.people_manager.find_person_by_name(raw_name)
            display = person.name if person is not None else raw_name.title()
            print(); print(f"¡Hola, {display}! Encantado de saludarte 👋")
            return True

        if self._handle_active_game(normalized):
            return True

        language_match = re.search(
            r"(?:clase|curso|aprender|practicar|profesor)\s+(?:de\s+)?(ingles|english|valenciano|catalan|frances|portugues|italiano|aleman)(?:\s+(basico|intermedio|avanzado))?",
            normalized,
        )
        if language_match:
            self._start_language_activity(
                language_match.group(1), language_match.group(2) or "basico", mode="lesson"
            )
            return True

        user = self._social_user()

        gratitude_markers = {
            "gracias", "muchas gracias", "mil gracias", "te lo agradezco",
            "perfecto gracias", "genial gracias", "vale gracias", "ok gracias",
        }
        if normalized in gratitude_markers or normalized.endswith(" gracias"):
            print(); print(random.choice((
                f"¡De nada, {user}! Para eso estoy.", f"Cuando quieras, {user}.",
                f"¡Un placer ayudarte, {user}!", "De nada. Me alegra que te haya servido.",
            )))
            return True

        if normalized in {"de nada", "no hay de que", "un placer"}:
            print(); print("Entonces quedamos en paz. Seguimos cuando quieras.")
            return True

        if any(marker in normalized for marker in ("felicidades", "enhorabuena", "feliz cumple", "feliz cumpleaños", "te felicito", "muy bien", "bien hecho")):
            print(); print(random.choice((
                f"¡Gracias, {user}! Lo recibo con orgullo digital y una humildad razonablemente creíble.",
                f"¡Muchas gracias, {user}! Me alegra que haya salido bien.",
                "¡Gracias! Lo celebraría con tarta, pero tendré que conformarme con unos cuantos ciclos de CPU.",
            )))
            return True

        if normalized in {"que tal", "que tal estas", "como estas", "como te encuentras"}:
            print(); print(random.choice((
                f"Estoy bien, {user}. No tengo cuerpo ni emociones humanas, pero estoy operativo y encantado de hablar contigo.",
                f"Todo en orden por aquí, {user}. No tengo días buenos o malos como una persona, pero mis procesos vienen con ganas de charla.",
                f"Funcionando y atento, {user}. ¿Cómo estás tú?",
            ))); return True

        if normalized in {"que haces", "que estas haciendo", "que andas haciendo"}:
            print(); print("Ahora mismo estoy aquí contigo, procesando lo que me dices. No hago cosas por mi cuenta fuera de Atlas, pero puedo charlar, ayudarte o jugar un rato."); return True

        explain_markers = {"no lo entiendo", "no entendi el chiste", "explica el chiste", "explicamelo", "por que hace gracia", "por que es gracioso"}
        if normalized in explain_markers or ("chiste" in normalized and "explica" in normalized):
            explanation = getattr(self, "_social_last_joke_explanation", None)
            if explanation:
                print(); print(explanation)
            else:
                print(); print("Todavía no te he contado un chiste en esta conversación. Pídeme uno y después te explico la gracia.")
            return True

        if "cuentame un chiste" in normalized or normalized in {"un chiste", "dime un chiste", "chiste"}:
            pool = list(self._HUMAN_JOKES) + list(self._AI_JOKES)
            if any(word in normalized for word in ("negro", "oscuro", "bestia")):
                pool += list(self._DARK_JOKES)
            joke, explanation = random.choice(pool)
            self._social_last_joke = joke
            self._social_last_joke_explanation = explanation
            print(); print(joke); return True

        if "humor negro" in normalized or "chiste negro" in normalized:
            joke, explanation = random.choice(self._DARK_JOKES)
            self._social_last_joke = joke
            self._social_last_joke_explanation = explanation
            print(); print(joke); return True

        if "frase de daxter" in normalized or "frases de daxter" in normalized:
            current = self.identity_manager.get_active_identity_name()
            self.identity_manager.change_identity("daxter", save_preference=False)
            phrase = self.identity_manager.get_phrase("game_quotes", default="¡Esto pide una entrada heroica y probablemente innecesaria!")
            self.identity_manager.change_identity(current, save_preference=False)
            print(); print(phrase); return True

        if "frase de coco" in normalized or "frases de coco" in normalized:
            current = self.identity_manager.get_active_identity_name()
            self.identity_manager.change_identity("coco", save_preference=False)
            phrase = self.identity_manager.get_phrase("game_quotes", default="Primero pensamos, luego pulsamos el botón peligroso.")
            self.identity_manager.change_identity(current, save_preference=False)
            print(); print(phrase); return True

        game_start_exact = {
            "jugar", "juguemos", "jugemos", "jugamos", "juguemos a algo", "jugemos a algo",
            "vamos a jugar", "vamos a jugar a algo", "vamos a jugar un juego", "jugar a algo",
            "juguemos un juego", "jugemos un juego", "quiero jugar", "quiero un juego",
            "pon un juego", "ponme un juego", "minijuego", "minijuegos", "menu de juegos",
            "que juegos tienes", "que podemos jugar", "a que podemos jugar",
        }
        if normalized in game_start_exact or any(phrase in normalized for phrase in ("vamos a jugar", "quiero jugar", "juguemos a", "jugemos a")):
            self._show_game_menu(); return True

        direct_game = self._game_selection(normalized)
        if direct_game:
            self._start_social_game(direct_game); return True

        if normalized in {"estoy aburrido", "estoy aburrida", "me aburro", "entretenme"}:
            self._show_game_menu(); return True

        if normalized in {"cuentame algo", "dime algo", "sorprendeme"}:
            print(); print(random.choice((
                "Dato curioso: los pulpos tienen tres corazones. Y aun así probablemente gestionan mejor el estrés que nosotros.",
                "Podemos empezar una historia por turnos: tú escribes una frase y yo continúo con otra.",
                "Pequeño reto: describe tu día usando solo tres palabras. Yo juzgaré con una objetividad sospechosa.",
                "Reto rápido: busca un objeto cercano cuyo nombre empiece por la última letra de tu nombre.",
            ))); return True

        return False
