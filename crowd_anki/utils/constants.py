from pathlib import Path

UUID_FIELD_NAME = 'crowdanki_uuid'
CSS_FIELD_NAME = 'css'
QFMT_FIELD_NAME = 'qfmt'
AFMT_FIELD_NAME = 'afmt'
TMPLS_FIELD_NAME = 'tmpls'
NOTE_MODELS_FIELD_NAME = 'note_models'

DECK_FILE_NAME = "deck"
NOTE_MODEL_FILE_NAME = "note_model"
STYLE_FILE_NAME = "style"
TMPL_FILE_NAME = "tmpl"
FRONT_FILE_NAME = "front"
BACK_FILE_NAME = "back"

STYLE_FILE_EXTENSION = ".css"
INDEX_FILE_EXTENSION = ".json"
FRONT_FILE_EXTENSION = ".html"
BACK_FILE_EXTENSION = ".html"

NOTE_MODELS_SUBDIRECTORY_NAME = "note_models"
TMPLS_SUBDIRECTORY_NAME = "tmpls"
MEDIA_SUBDIRECTORY_NAME = "media"

IMPORT_CONFIG_NAME = "import_config.yaml"

ANKI_EXPORT_EXTENSION = "directory"

USER_FILES_PATH = Path(__file__).parent.parent.joinpath('user_files')
