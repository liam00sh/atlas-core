"""
===============================================================================
Proyecto Atlas
Archivo: identity/family_data.py

Descripción:
    Contiene los datos familiares iniciales del Proyecto Atlas.

    Este archivo es declarativo:

    - No escribe archivos.
    - No crea objetos Person.
    - No crea objetos Animal.
    - No crea relaciones directamente.

    FamilyInitializer utiliza estas colecciones para registrar
    personas, animales y relaciones sin duplicar información.
===============================================================================
"""


# =============================================================================
# PERSONAS
# =============================================================================

FAMILY_PEOPLE = [
    {
        "name": "Liam Vicente Martínez",
        "aliases": [
            "Liam",
            "Nerea Vicente Martínez",
            "Nerea Vicente",
        ],
        "grammatical_gender": "masculine",
        "user_profile": "Liam",
        "summary": (
            "Usuario principal de Atlas. Hombre trans. "
            "Nerea Vicente Martínez es su nombre anterior y solo debe "
            "utilizarse para reconocer documentos antiguos, nunca como "
            "forma habitual de dirigirse a él. Vive en Beneixama."
        ),
    },
    {
        "name": "Saray Izquierdo Carreres",
        "aliases": [
            "Saray",
        ],
        "grammatical_gender": "feminine",
        "user_profile": "Saray",
        "summary": (
            "Pareja de Liam. Vive en Caudete y estudia en Alicante."
        ),
    },
    {
        "name": "José Vicente Navarro",
        "aliases": [
            "José",
            "Padre de Liam",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Padre de Liam. Vive en Beneixama."
        ),
    },
    {
        "name": "María José Martínez Sanz",
        "aliases": [
            "Mary",
            "Madre de Liam",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Madre de Liam. Vive en Beneixama."
        ),
    },
    {
        "name": "José Manuel Martínez Pérez",
        "aliases": [
            "Txipi",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Primo biológico de Liam y hermano adoptivo o afectivo. "
            "Fue adoptado por la madre de Liam tras quedar huérfano. "
            "Vive en Villena con su mujer Sara y su hijo Adra."
        ),
    },
    {
        "name": "Sara",
        "aliases": [
            "Sara, mujer de Txipi",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Mujer de Txipi y madre de Adra."
        ),
    },
    {
        "name": "Adra",
        "aliases": [],
        "grammatical_gender": "masculine",
        "summary": (
            "Hijo pequeño de Txipi y Sara. Tiene aproximadamente "
            "dos años."
        ),
    },
    {
        "name": "Alba Martínez Pérez",
        "aliases": [
            "Alba",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Prima biológica de Liam y hermana adoptiva o afectiva. "
            "Tras fallecer sus padres vivió con familiares de Liam. "
            "Suele vivir con su novio Pablo o pasar algunos fines "
            "de semana en Beneixama."
        ),
    },
    {
        "name": "Pablo",
        "aliases": [
            "Pablo, novio de Alba",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Pareja de Alba. Relacionado con Monforte."
        ),
    },
    {
        "name": "Raúl Vicente Martínez",
        "aliases": [
            "Raúl",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Hermano de Liam. Vive habitualmente en Barcelona."
        ),
    },
    {
        "name": "Lidia Vicente Martínez",
        "aliases": [
            "Lidia",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Hermana de Liam."
        ),
    },
    {
        "name": "Roberto Amarillo Navarro",
        "aliases": [
            "Roberto",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Pareja de Lidia."
        ),
    },

    # -------------------------------------------------------------------------
    # FAMILIA PATERNA DE LIAM
    # -------------------------------------------------------------------------

    {
        "name": "Fermina Navarro",
        "aliases": [
            "Fermina",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Abuela paterna biológica de Liam. Falleció al nacer "
            "José Vicente Navarro."
        ),
    },
    {
        "name": "José Vicente",
        "aliases": [
            "Pepe",
            "Abuelo Pepe",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Abuelo paterno de Liam. Fallecido."
        ),
    },
    {
        "name": "Lola Payá",
        "aliases": [
            "Abuela Lola",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Segunda mujer del abuelo paterno de Liam y abuela "
            "afectiva de Liam."
        ),
    },
    {
        "name": "Pepi Vicente Navarro",
        "aliases": [
            "Pepi",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Tía paterna de Liam."
        ),
    },
    {
        "name": "Salvador Amorós",
        "aliases": [],
        "grammatical_gender": "masculine",
        "summary": (
            "Marido de Pepi Vicente Navarro."
        ),
    },
    {
        "name": "Salvador Amorós Vicente",
        "aliases": [],
        "grammatical_gender": "masculine",
        "summary": (
            "Primo paterno de Liam."
        ),
    },
    {
        "name": "Mario Amorós Vicente",
        "aliases": [],
        "grammatical_gender": "masculine",
        "summary": (
            "Primo paterno de Liam. Tiene una casa en El Salse, "
            "pedanía de Beneixama."
        ),
    },
    {
        "name": "Francisco Vicente Payá",
        "aliases": [
            "Francisco",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Tío paterno de Liam. Vive en Madrid."
        ),
    },
    {
        "name": "Lucía",
        "aliases": [
            "Lucía, mujer de Francisco",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Mujer de Francisco Vicente Payá. Vive en Madrid."
        ),
    },
    {
        "name": "Claudia Vicente",
        "aliases": [
            "Claudia",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Prima paterna de Liam. Vive en Madrid."
        ),
    },
    {
        "name": "Martín Vicente",
        "aliases": [
            "Martín",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Primo paterno de Liam. Vive en Madrid."
        ),
    },

    # -------------------------------------------------------------------------
    # FAMILIA MATERNA DE LIAM
    # -------------------------------------------------------------------------

    {
        "name": "Pepe Martínez",
        "aliases": [
            "Abuelo materno de Liam",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Abuelo materno de Liam. Fallecido."
        ),
    },
    {
        "name": "Consuelo Sanz Esteve",
        "aliases": [
            "Abuela materna de Liam",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Abuela materna de Liam. Fallecida."
        ),
    },
    {
        "name": "Manolo Martínez Sanz",
        "aliases": [
            "Manolo",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Tío materno de Liam. Padre biológico de Txipi y Alba. "
            "Fallecido."
        ),
    },
    {
        "name": "Fermina Pérez",
        "aliases": [],
        "grammatical_gender": "feminine",
        "summary": (
            "Mujer de Manolo Martínez Sanz y madre biológica "
            "de Txipi y Alba. Fallecida."
        ),
    },
    {
        "name": "Consuelo Martínez Sanz",
        "aliases": [
            "Chelo",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Tía materna de Liam. Existe distanciamiento familiar "
            "entre ella y la unidad familiar de Liam."
        ),
    },
    {
        "name": "Evaristo Maestre",
        "aliases": [
            "Evaristo",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Marido de Chelo. Existe distanciamiento familiar."
        ),
    },
    {
        "name": "María Teresa Maestre Martínez",
        "aliases": [
            "María Teresa",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Prima materna de Liam."
        ),
    },
    {
        "name": "Evaristo Maestre Martínez",
        "aliases": [
            "Evaristo hijo",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Primo materno de Liam."
        ),
    },

    # -------------------------------------------------------------------------
    # FAMILIA DE SARAY
    # -------------------------------------------------------------------------

    {
        "name": "José Miguel Izquierdo Catalán",
        "aliases": [
            "Padre de Saray",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Padre de Saray. Tuvo una relación anterior antes "
            "de estar con Pepi Carreres López."
        ),
    },
    {
        "name": "Pepi Carreres López",
        "aliases": [
            "Madre de Saray",
            "Pepi",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Madre de Saray. Mantiene una relación muy cercana "
            "con su hermana Manoli."
        ),
    },
    {
        "name": "Rubén Izquierdo Carreres",
        "aliases": [
            "Rubén",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Hermano de Saray. Es reservado y Liam todavía "
            "no lo conoce demasiado."
        ),
    },
    {
        "name": "Manuela López Serrano",
        "aliases": [
            "Abuela materna de Saray",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Abuela materna de Saray. Vive en Caudete y tiene demencia."
        ),
    },
    {
        "name": "Antonio Carreres Hernández",
        "aliases": [
            "Abuelo materno de Saray",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Abuelo materno de Saray. Vive en Caudete."
        ),
    },
    {
        "name": "Andrés Carreres López",
        "aliases": [],
        "grammatical_gender": "masculine",
        "summary": (
            "Tío materno de Saray."
        ),
    },
    {
        "name": "Antonio Carreres López",
        "aliases": [],
        "grammatical_gender": "masculine",
        "summary": (
            "Tío materno de Saray."
        ),
    },
    {
        "name": "Yael Carreres",
        "aliases": [
            "Yael",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Prima de Saray e hija de Antonio Carreres López."
        ),
    },
    {
        "name": "Yeray Carreres",
        "aliases": [
            "Yeray",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Primo de Saray e hijo de Antonio Carreres López."
        ),
    },
    {
        "name": "Jorge Carreres López",
        "aliases": [],
        "grammatical_gender": "masculine",
        "summary": (
            "Tío materno de Saray."
        ),
    },
    {
        "name": "Manoli Carreres López",
        "aliases": [
            "Manoli",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Tía materna de Saray. Tiene una relación muy cercana "
            "con Saray, Liam y su hermana Pepi."
        ),
    },
    {
        "name": "Georgel Melinte",
        "aliases": [
            "Marido de Manoli",
        ],
        "grammatical_gender": "masculine",
        "summary": (
            "Marido rumano de Manoli. Dispone de un campo en Caudete "
            "cedido o prestado por su jefe."
        ),
    },
    {
        "name": "Noa Melinte Carreres",
        "aliases": [
            "Noa",
        ],
        "grammatical_gender": "feminine",
        "summary": (
            "Prima de Saray e hija de Manoli y Georgel. Mantiene una "
            "relación cercana con Liam y Saray."
        ),
    },
]


# =============================================================================
# ANIMALES
# =============================================================================

FAMILY_ANIMALS = [
    {
        "name": "Don Gato Mishi Van Gogh",
        "aliases": [
            "Don Gato",
            "Mishi",
            "Van Gogh",
            "Gato",
        ],
        "species": "cat",
        "sex": "male",
        "grammatical_gender": "masculine",
        "summary": (
            "Gato de Liam. Vive en la unidad familiar de Beneixama."
        ),
    },
    {
        "name": "Funcionario",
        "aliases": [
            "Funcio",
        ],
        "species": "cat",
        "sex": "male",
        "grammatical_gender": "masculine",
        "summary": (
            "Gato de Lidia. Vive en la unidad familiar de Beneixama."
        ),
    },
    {
        "name": "Lucas",
        "aliases": [
            "Lucas, gato de Roberto",
        ],
        "species": "cat",
        "sex": "male",
        "grammatical_gender": "masculine",
        "summary": (
            "Gato de Roberto."
        ),
    },
    {
        "name": "Estrella",
        "aliases": [],
        "species": "dog",
        "sex": "female",
        "grammatical_gender": "feminine",
        "summary": (
            "Perra de los abuelos maternos de Saray. Suele acompañar "
            "a Liam y Saray cuando van al campo."
        ),
    },
]


# =============================================================================
# RELACIONES
# =============================================================================

FAMILY_RELATIONSHIPS = [{'source': 'María José Martínez Sanz',
  'relationship_type': 'mother',
  'target': 'Liam Vicente Martínez',
  'notes': 'Madre biológica.'},
 {'source': 'José Vicente Navarro',
  'relationship_type': 'father',
  'target': 'Liam Vicente Martínez',
  'notes': 'Padre biológico.'},
 {'source': 'Raúl Vicente Martínez',
  'relationship_type': 'brother',
  'target': 'Liam Vicente Martínez',
  'notes': ''},
 {'source': 'Lidia Vicente Martínez',
  'relationship_type': 'sister',
  'target': 'Liam Vicente Martínez',
  'notes': ''},
 {'source': 'Liam Vicente Martínez',
  'relationship_type': 'partner',
  'target': 'Saray Izquierdo Carreres',
  'notes': ''},
 {'source': 'José Manuel Martínez Pérez',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Primo biológico.'},
 {'source': 'José Manuel Martínez Pérez',
  'relationship_type': 'brother',
  'target': 'Liam Vicente Martínez',
  'notes': 'Hermano adoptivo y afectivo. Fue criado por la familia de Liam tras quedar '
           'huérfano.'},
 {'source': 'Alba Martínez Pérez',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Prima biológica.'},
 {'source': 'Alba Martínez Pérez',
  'relationship_type': 'sister',
  'target': 'Liam Vicente Martínez',
  'notes': 'Hermana adoptiva y afectiva. Fue criada por familiares de Liam tras quedar '
           'huérfana.'},
 {'source': 'José Manuel Martínez Pérez',
  'relationship_type': 'partner',
  'target': 'Sara',
  'notes': ''},
 {'source': 'José Manuel Martínez Pérez',
  'relationship_type': 'father',
  'target': 'Adra',
  'notes': ''},
 {'source': 'Sara', 'relationship_type': 'mother', 'target': 'Adra', 'notes': ''},
 {'source': 'Alba Martínez Pérez',
  'relationship_type': 'partner',
  'target': 'Pablo',
  'notes': ''},
 {'source': 'Lidia Vicente Martínez',
  'relationship_type': 'partner',
  'target': 'Roberto Amarillo Navarro',
  'notes': ''},
 {'source': 'Liam Vicente Martínez',
  'source_type': 'person',
  'relationship_type': 'pet_owner',
  'target': 'Don Gato Mishi Van Gogh',
  'target_type': 'animal',
  'notes': ''},
 {'source': 'Lidia Vicente Martínez',
  'source_type': 'person',
  'relationship_type': 'pet_owner',
  'target': 'Funcionario',
  'target_type': 'animal',
  'notes': ''},
 {'source': 'Roberto Amarillo Navarro',
  'source_type': 'person',
  'relationship_type': 'pet_owner',
  'target': 'Lucas',
  'target_type': 'animal',
  'notes': ''},
 {'source': 'Manuela López Serrano',
  'source_type': 'person',
  'relationship_type': 'pet_owner',
  'target': 'Estrella',
  'target_type': 'animal',
  'notes': 'Responsabilidad compartida con Antonio Carreres Hernández.'},
 {'source': 'Antonio Carreres Hernández',
  'source_type': 'person',
  'relationship_type': 'cares_for',
  'target': 'Estrella',
  'target_type': 'animal',
  'notes': ''},
 {'source': 'María José Martínez Sanz',
  'relationship_type': 'mother',
  'target': 'Raúl Vicente Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'José Vicente Navarro',
  'relationship_type': 'father',
  'target': 'Raúl Vicente Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'María José Martínez Sanz',
  'relationship_type': 'mother',
  'target': 'Lidia Vicente Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'José Vicente Navarro',
  'relationship_type': 'father',
  'target': 'Lidia Vicente Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'María José Martínez Sanz',
  'relationship_type': 'partner',
  'target': 'José Vicente Navarro',
  'notes': 'Padres de Liam, Raúl y Lidia.'},
 {'source': 'Raúl Vicente Martínez',
  'relationship_type': 'brother',
  'target': 'Lidia Vicente Martínez',
  'notes': 'Hermanos biológicos.'},
 {'source': 'María José Martínez Sanz',
  'relationship_type': 'mother',
  'target': 'José Manuel Martínez Pérez',
  'notes': 'Madre adoptiva de Txipi.'},
 {'source': 'José Manuel Martínez Pérez',
  'relationship_type': 'brother',
  'target': 'Alba Martínez Pérez',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Fermina Navarro',
  'relationship_type': 'partner',
  'target': 'José Vicente',
  'notes': 'Primera pareja; Fermina falleció al nacer José Vicente Navarro.'},
 {'source': 'José Vicente',
  'relationship_type': 'partner',
  'target': 'Lola Payá',
  'notes': 'Segunda pareja de José Vicente.'},
 {'source': 'Pepi Vicente Navarro',
  'relationship_type': 'partner',
  'target': 'Salvador Amorós',
  'notes': 'Matrimonio.'},
 {'source': 'Francisco Vicente Payá',
  'relationship_type': 'partner',
  'target': 'Lucía',
  'notes': 'Matrimonio.'},
 {'source': 'Fermina Navarro',
  'relationship_type': 'mother',
  'target': 'Pepi Vicente Navarro',
  'notes': 'Relación biológica.'},
 {'source': 'Fermina Navarro',
  'relationship_type': 'mother',
  'target': 'José Vicente Navarro',
  'notes': 'Relación biológica.'},
 {'source': 'José Vicente',
  'relationship_type': 'father',
  'target': 'Pepi Vicente Navarro',
  'notes': 'Relación biológica.'},
 {'source': 'José Vicente',
  'relationship_type': 'father',
  'target': 'José Vicente Navarro',
  'notes': 'Relación biológica.'},
 {'source': 'José Vicente',
  'relationship_type': 'father',
  'target': 'Francisco Vicente Payá',
  'notes': 'Relación biológica.'},
 {'source': 'Lola Payá',
  'relationship_type': 'mother',
  'target': 'Francisco Vicente Payá',
  'notes': 'Relación biológica.'},
 {'source': 'Pepi Vicente Navarro',
  'relationship_type': 'mother',
  'target': 'Salvador Amorós Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Pepi Vicente Navarro',
  'relationship_type': 'mother',
  'target': 'Mario Amorós Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Salvador Amorós',
  'relationship_type': 'father',
  'target': 'Salvador Amorós Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Salvador Amorós',
  'relationship_type': 'father',
  'target': 'Mario Amorós Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Francisco Vicente Payá',
  'relationship_type': 'father',
  'target': 'Claudia Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Francisco Vicente Payá',
  'relationship_type': 'father',
  'target': 'Martín Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Lucía',
  'relationship_type': 'mother',
  'target': 'Claudia Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Lucía',
  'relationship_type': 'mother',
  'target': 'Martín Vicente',
  'notes': 'Relación biológica.'},
 {'source': 'Pepi Vicente Navarro',
  'relationship_type': 'sister',
  'target': 'José Vicente Navarro',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Francisco Vicente Payá',
  'relationship_type': 'brother',
  'target': 'José Vicente Navarro',
  'notes': 'Hermanos por parte de padre.'},
 {'source': 'Francisco Vicente Payá',
  'relationship_type': 'brother',
  'target': 'Pepi Vicente Navarro',
  'notes': 'Hermanos por parte de padre.'},
 {'source': 'Salvador Amorós Vicente',
  'relationship_type': 'brother',
  'target': 'Mario Amorós Vicente',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Claudia Vicente',
  'relationship_type': 'sister',
  'target': 'Martín Vicente',
  'notes': 'Hermanos biológicos.'},
 {'source': 'José Vicente',
  'relationship_type': 'grandfather',
  'target': 'Liam Vicente Martínez',
  'notes': 'Abuelo paterno.'},
 {'source': 'Fermina Navarro',
  'relationship_type': 'grandmother',
  'target': 'Liam Vicente Martínez',
  'notes': 'Abuela paterna biológica.'},
 {'source': 'Lola Payá',
  'relationship_type': 'grandmother',
  'target': 'Liam Vicente Martínez',
  'notes': 'Abuela paterna afectiva.'},
 {'source': 'Pepi Vicente Navarro',
  'relationship_type': 'aunt',
  'target': 'Liam Vicente Martínez',
  'notes': 'Tía paterna.'},
 {'source': 'Francisco Vicente Payá',
  'relationship_type': 'uncle',
  'target': 'Liam Vicente Martínez',
  'notes': 'Tío paterno.'},
 {'source': 'Salvador Amorós Vicente',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Primo paterno.'},
 {'source': 'Mario Amorós Vicente',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Primo paterno.'},
 {'source': 'Claudia Vicente',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Prima paterna.'},
 {'source': 'Martín Vicente',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Primo paterno.'},
 {'source': 'Pepe Martínez',
  'relationship_type': 'partner',
  'target': 'Consuelo Sanz Esteve',
  'notes': 'Abuelos maternos de Liam.'},
 {'source': 'Pepe Martínez',
  'relationship_type': 'father',
  'target': 'Manolo Martínez Sanz',
  'notes': 'Relación biológica.'},
 {'source': 'Pepe Martínez',
  'relationship_type': 'father',
  'target': 'Consuelo Martínez Sanz',
  'notes': 'Relación biológica.'},
 {'source': 'Pepe Martínez',
  'relationship_type': 'father',
  'target': 'María José Martínez Sanz',
  'notes': 'Relación biológica.'},
 {'source': 'Consuelo Sanz Esteve',
  'relationship_type': 'mother',
  'target': 'Manolo Martínez Sanz',
  'notes': 'Relación biológica.'},
 {'source': 'Consuelo Sanz Esteve',
  'relationship_type': 'mother',
  'target': 'Consuelo Martínez Sanz',
  'notes': 'Relación biológica.'},
 {'source': 'Consuelo Sanz Esteve',
  'relationship_type': 'mother',
  'target': 'María José Martínez Sanz',
  'notes': 'Relación biológica.'},
 {'source': 'Manolo Martínez Sanz',
  'relationship_type': 'father',
  'target': 'José Manuel Martínez Pérez',
  'notes': 'Relación biológica.'},
 {'source': 'Manolo Martínez Sanz',
  'relationship_type': 'father',
  'target': 'Alba Martínez Pérez',
  'notes': 'Relación biológica.'},
 {'source': 'Fermina Pérez',
  'relationship_type': 'mother',
  'target': 'José Manuel Martínez Pérez',
  'notes': 'Relación biológica.'},
 {'source': 'Fermina Pérez',
  'relationship_type': 'mother',
  'target': 'Alba Martínez Pérez',
  'notes': 'Relación biológica.'},
 {'source': 'Consuelo Martínez Sanz',
  'relationship_type': 'mother',
  'target': 'María Teresa Maestre Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'Consuelo Martínez Sanz',
  'relationship_type': 'mother',
  'target': 'Evaristo Maestre Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'Evaristo Maestre',
  'relationship_type': 'father',
  'target': 'María Teresa Maestre Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'Evaristo Maestre',
  'relationship_type': 'father',
  'target': 'Evaristo Maestre Martínez',
  'notes': 'Relación biológica.'},
 {'source': 'Manolo Martínez Sanz',
  'relationship_type': 'partner',
  'target': 'Fermina Pérez',
  'notes': 'Padres biológicos de Txipi y Alba; ambos fallecidos.'},
 {'source': 'Consuelo Martínez Sanz',
  'relationship_type': 'partner',
  'target': 'Evaristo Maestre',
  'notes': 'Matrimonio.'},
 {'source': 'Manolo Martínez Sanz',
  'relationship_type': 'brother',
  'target': 'María José Martínez Sanz',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Consuelo Martínez Sanz',
  'relationship_type': 'sister',
  'target': 'María José Martínez Sanz',
  'notes': 'Hermanas biológicas.'},
 {'source': 'Manolo Martínez Sanz',
  'relationship_type': 'brother',
  'target': 'Consuelo Martínez Sanz',
  'notes': 'Hermanos biológicos.'},
 {'source': 'María Teresa Maestre Martínez',
  'relationship_type': 'sister',
  'target': 'Evaristo Maestre Martínez',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Pepe Martínez',
  'relationship_type': 'grandfather',
  'target': 'Liam Vicente Martínez',
  'notes': 'Abuelo materno.'},
 {'source': 'Consuelo Sanz Esteve',
  'relationship_type': 'grandmother',
  'target': 'Liam Vicente Martínez',
  'notes': 'Abuela materna.'},
 {'source': 'Manolo Martínez Sanz',
  'relationship_type': 'uncle',
  'target': 'Liam Vicente Martínez',
  'notes': 'Tío materno.'},
 {'source': 'Consuelo Martínez Sanz',
  'relationship_type': 'aunt',
  'target': 'Liam Vicente Martínez',
  'notes': 'Tía materna; existe distanciamiento familiar.'},
 {'source': 'María Teresa Maestre Martínez',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Prima materna.'},
 {'source': 'Evaristo Maestre Martínez',
  'relationship_type': 'cousin',
  'target': 'Liam Vicente Martínez',
  'notes': 'Primo materno.'},
 {'source': 'José Miguel Izquierdo Catalán',
  'relationship_type': 'partner',
  'target': 'Pepi Carreres López',
  'notes': 'Padres de Saray y Rubén.'},
 {'source': 'José Miguel Izquierdo Catalán',
  'relationship_type': 'father',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Relación biológica.'},
 {'source': 'José Miguel Izquierdo Catalán',
  'relationship_type': 'father',
  'target': 'Rubén Izquierdo Carreres',
  'notes': 'Relación biológica.'},
 {'source': 'Pepi Carreres López',
  'relationship_type': 'mother',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Relación biológica.'},
 {'source': 'Pepi Carreres López',
  'relationship_type': 'mother',
  'target': 'Rubén Izquierdo Carreres',
  'notes': 'Relación biológica.'},
 {'source': 'Antonio Carreres Hernández',
  'relationship_type': 'father',
  'target': 'Andrés Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Antonio Carreres Hernández',
  'relationship_type': 'father',
  'target': 'Pepi Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Antonio Carreres Hernández',
  'relationship_type': 'father',
  'target': 'Antonio Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Antonio Carreres Hernández',
  'relationship_type': 'father',
  'target': 'Jorge Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Antonio Carreres Hernández',
  'relationship_type': 'father',
  'target': 'Manoli Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Manuela López Serrano',
  'relationship_type': 'mother',
  'target': 'Andrés Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Manuela López Serrano',
  'relationship_type': 'mother',
  'target': 'Pepi Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Manuela López Serrano',
  'relationship_type': 'mother',
  'target': 'Antonio Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Manuela López Serrano',
  'relationship_type': 'mother',
  'target': 'Jorge Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Manuela López Serrano',
  'relationship_type': 'mother',
  'target': 'Manoli Carreres López',
  'notes': 'Relación biológica.'},
 {'source': 'Antonio Carreres López',
  'relationship_type': 'father',
  'target': 'Yael Carreres',
  'notes': 'Relación biológica.'},
 {'source': 'Antonio Carreres López',
  'relationship_type': 'father',
  'target': 'Yeray Carreres',
  'notes': 'Relación biológica.'},
 {'source': 'Manoli Carreres López',
  'relationship_type': 'partner',
  'target': 'Georgel Melinte',
  'notes': 'Matrimonio.'},
 {'source': 'Manoli Carreres López',
  'relationship_type': 'mother',
  'target': 'Noa Melinte Carreres',
  'notes': 'Madre biológica.'},
 {'source': 'Georgel Melinte',
  'relationship_type': 'father',
  'target': 'Noa Melinte Carreres',
  'notes': 'Padre biológico.'},
 {'source': 'Rubén Izquierdo Carreres',
  'relationship_type': 'brother',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Antonio Carreres Hernández',
  'relationship_type': 'partner',
  'target': 'Manuela López Serrano',
  'notes': 'Abuelos maternos de Saray.'},
 {'source': 'Andrés Carreres López',
  'relationship_type': 'brother',
  'target': 'Pepi Carreres López',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Antonio Carreres López',
  'relationship_type': 'brother',
  'target': 'Pepi Carreres López',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Jorge Carreres López',
  'relationship_type': 'brother',
  'target': 'Pepi Carreres López',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Manoli Carreres López',
  'relationship_type': 'sister',
  'target': 'Pepi Carreres López',
  'notes': 'Hermanas biológicas y relación cercana.'},
 {'source': 'Yael Carreres',
  'relationship_type': 'sister',
  'target': 'Yeray Carreres',
  'notes': 'Hermanos biológicos.'},
 {'source': 'Antonio Carreres Hernández',
  'relationship_type': 'grandfather',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Abuelo materno.'},
 {'source': 'Manuela López Serrano',
  'relationship_type': 'grandmother',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Abuela materna.'},
 {'source': 'Andrés Carreres López',
  'relationship_type': 'uncle',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Tío materno.'},
 {'source': 'Antonio Carreres López',
  'relationship_type': 'uncle',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Tío materno.'},
 {'source': 'Jorge Carreres López',
  'relationship_type': 'uncle',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Tío materno.'},
 {'source': 'Manoli Carreres López',
  'relationship_type': 'aunt',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Tía materna y relación cercana.'},
 {'source': 'Yael Carreres',
  'relationship_type': 'cousin',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Prima materna.'},
 {'source': 'Yeray Carreres',
  'relationship_type': 'cousin',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Primo materno.'},
 {'source': 'Noa Melinte Carreres',
  'relationship_type': 'cousin',
  'target': 'Saray Izquierdo Carreres',
  'notes': 'Prima materna y relación cercana.'},
 {'source': 'Liam Vicente Martínez',
  'relationship_type': 'cares_for',
  'target': 'Estrella',
  'notes': 'Estrella acompaña con frecuencia a Liam y Saray al campo.',
  'source_type': 'person',
  'target_type': 'animal'},
 {'source': 'Saray Izquierdo Carreres',
  'relationship_type': 'cares_for',
  'target': 'Estrella',
  'notes': 'Estrella acompaña con frecuencia a Liam y Saray al campo.',
  'source_type': 'person',
  'target_type': 'animal'}]
