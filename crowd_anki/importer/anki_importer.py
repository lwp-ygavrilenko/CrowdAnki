import json
import os
import shutil
from pathlib import Path
from typing import Callable, Optional

import aqt
import aqt.utils
import yaml

from ..representation import deck_initializer
from ..utils.constants import (AFMT_FIELD_NAME, BACK_FILE_EXTENSION,
                               BACK_FILE_NAME, CSS_FIELD_NAME, DECK_FILE_NAME,
                               FRONT_FILE_EXTENSION, FRONT_FILE_NAME,
                               IMPORT_CONFIG_NAME, INDEX_FILE_EXTENSION,
                               MEDIA_SUBDIRECTORY_NAME, NOTE_MODEL_FILE_NAME,
                               NOTE_MODELS_FIELD_NAME,
                               NOTE_MODELS_SUBDIRECTORY_NAME, QFMT_FIELD_NAME,
                               STYLE_FILE_EXTENSION, STYLE_FILE_NAME,
                               TMPL_FILE_NAME, TMPLS_FIELD_NAME,
                               TMPLS_SUBDIRECTORY_NAME)
from ..importer.import_dialog import ImportDialog, ImportConfig
from aqt.qt import QDialog


class AnkiJsonImporter:
    def __init__(self, collection, deck_file_name: str = DECK_FILE_NAME):
        self.collection = collection
        self.deck_file_name = deck_file_name

    def load_deck(self, directory_path: Path) -> bool:
        """
        Load deck serialized to directory
        Assumes that deck json file is located in the directory
        and named 'deck.json' or '[foldername].json along with other files
        :param directory_path: Path
        """
        deck_path = self.get_deck_path(directory_path)
        if not deck_path.exists():
            raise ValueError("There is no {} file inside of the selected directory".format(deck_path))
        deck_json = self.read_json_file(deck_path)

        note_models_directory_path = directory_path.joinpath(NOTE_MODELS_SUBDIRECTORY_NAME)
        if not note_models_directory_path.exists():
            raise ValueError("There is no {} directory inside of the selected directory".format(note_models_directory_path))
        note_models = []
        for note_model_directory_path in filter(Path.is_dir, note_models_directory_path.iterdir()):
            note_model_json = self.read_json_file(note_model_directory_path.joinpath(NOTE_MODEL_FILE_NAME).with_suffix(INDEX_FILE_EXTENSION))

            note_model_json[CSS_FIELD_NAME] = self.read_text_file(note_model_directory_path.joinpath(STYLE_FILE_NAME).with_suffix(STYLE_FILE_EXTENSION))

            tmpls_directory_path = note_model_directory_path.joinpath(TMPLS_SUBDIRECTORY_NAME)
            if not tmpls_directory_path.exists():
                raise ValueError("There is no {} directory inside of the note model directory".format(tmpls_directory_path))
            tmpls = []
            for tmpl_directory_path in filter(Path.is_dir, tmpls_directory_path.iterdir()):
                tmpl_json = self.read_json_file(tmpl_directory_path.joinpath(TMPL_FILE_NAME).with_suffix(INDEX_FILE_EXTENSION))

                tmpl_json[AFMT_FIELD_NAME] = self.read_text_file(tmpl_directory_path.joinpath(BACK_FILE_NAME).with_suffix(BACK_FILE_EXTENSION))
                tmpl_json[QFMT_FIELD_NAME] = self.read_text_file(tmpl_directory_path.joinpath(FRONT_FILE_NAME).with_suffix(FRONT_FILE_EXTENSION))

                tmpls.append(tmpl_json)
            note_model_json[TMPLS_FIELD_NAME] = tmpls
            
            note_models.append(note_model_json)
        deck_json[NOTE_MODELS_FIELD_NAME] = note_models

        import_config = self.read_import_config(directory_path, deck_json)
        if import_config is None:
            return False

        if aqt.mw:
            aqt.mw.create_backup_now()
        try:
            deck = deck_initializer.from_json(deck_json)
            deck.save_to_collection(self.collection, import_config=import_config)

            if import_config.use_media:
                self.import_media(directory_path)
        finally:
            if aqt.mw:
                aqt.mw.deckBrowser.show()
        return True

    def import_media(self, directory_path):
        media_directory = directory_path.joinpath(MEDIA_SUBDIRECTORY_NAME)
        if media_directory.exists():
            unicode_media_directory = str(media_directory)
            src_files = os.listdir(unicode_media_directory)
            for filename in src_files:
                full_filename = os.path.join(unicode_media_directory, filename)
                if os.path.isfile(full_filename):
                    shutil.copy(full_filename, self.collection.media.dir())
        else:
            print("Warning: no media directory exists.")

    def get_deck_path(self, directory_path):
        """
        Provides compatibility layer between deck file naming conventions.
        Assumes that deck json file is located in the directory and named 'deck.json'
        """

        def path_for_name(name):
            return directory_path.joinpath(name).with_suffix(INDEX_FILE_EXTENSION)

        convention_path = path_for_name(self.deck_file_name)   # [folder]/deck.json
        inferred_path = path_for_name(directory_path.name)     # [folder]/[folder].json
        return convention_path if convention_path.exists() else inferred_path

    @staticmethod
    def read_json_file(file_path):
        return AnkiJsonImporter.read_file(file_path, lambda file: json.load(file))

    @staticmethod
    def read_text_file(file_path):
        return AnkiJsonImporter.read_file(file_path, lambda file: file.read())

    @staticmethod
    def read_file(file_path: Path, extract_content):
        with file_path.open(encoding='utf8') as file:
            return extract_content(file)

    @staticmethod
    def read_import_config(directory_path, deck_json):
        file_path = directory_path.joinpath(IMPORT_CONFIG_NAME)

        if not file_path.exists():
            import_dict = {}
        else:
            with file_path.open(encoding='utf8') as meta_file:
                import_dict = yaml.full_load(meta_file)

        import_dialog = ImportDialog(deck_json, import_dict)
        if import_dialog.exec() == QDialog.DialogCode.Rejected:
            return None

        return import_dialog.final_import_config

    @staticmethod
    def import_deck_from_path(collection, directory_path):
        importer = AnkiJsonImporter(collection)
        try:
            if importer.load_deck(directory_path):
                aqt.utils.showInfo("Import of {} deck was successful".format(directory_path.name))
        except ValueError as error:
            aqt.utils.showWarning("Error: {}. While trying to import deck from directory {}".format(
                error.args[0], directory_path))
            raise

    @staticmethod
    def import_deck(collection, directory_provider: Callable[[str], Optional[str]]):
        directory_path = str(directory_provider("Select Deck Directory"))
        if directory_path:
            AnkiJsonImporter.import_deck_from_path(collection, Path(directory_path))
