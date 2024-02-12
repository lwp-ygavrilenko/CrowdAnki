import json
import os

import shutil
from pathlib import Path
from typing import Callable


from .deck_exporter import DeckExporter
from ..anki.adapters.anki_deck import AnkiDeck
from ..representation import deck_initializer
from ..representation.serializable import Serializable
from ..utils.constants import (AFMT_FIELD_NAME, BACK_FILE_EXTENSION,
                               BACK_FILE_NAME, CSS_FIELD_NAME, DECK_FILE_NAME,
                               FRONT_FILE_EXTENSION, FRONT_FILE_NAME,
                               INDEX_FILE_EXTENSION, MEDIA_SUBDIRECTORY_NAME,
                               NOTE_MODEL_FILE_NAME,
                               NOTE_MODELS_SUBDIRECTORY_NAME, QFMT_FIELD_NAME,
                               STYLE_FILE_EXTENSION, STYLE_FILE_NAME,
                               TMPL_FILE_NAME, TMPLS_FIELD_NAME,
                               TMPLS_SUBDIRECTORY_NAME)
from ..utils.filesystem.name_sanitizer import sanitize_anki_name
from .note_sorter import NoteSorter
from ..config.config_settings import ConfigSettings


class AnkiExporter(DeckExporter):
    def __init__(self, collection,
                 config: ConfigSettings,
                 name_sanitizer: Callable[[str], str] = sanitize_anki_name,
                 deck_file_name: str = DECK_FILE_NAME):
        self.config = config
        self.collection = collection
        self.last_exported_count = 0
        self.name_sanitizer = name_sanitizer
        self.deck_file_name = deck_file_name
        self.note_sorter = NoteSorter(config)

    def export_to_directory(self, deck: AnkiDeck, output_dir=Path("."), copy_media=True, create_deck_subdirectory=True) -> Path:
        deck_directory = output_dir
        if create_deck_subdirectory:
            deck_directory= self._make_directory(output_dir, self.name_sanitizer(deck.name))

        deck = deck_initializer.from_collection(self.collection, deck.name)

        self.note_sorter.sort_deck(deck)

        self.last_exported_count = deck.get_note_count()

        self._write_index_file(deck_directory, self.deck_file_name, deck)

        note_models_directory = self._make_directory(deck_directory, NOTE_MODELS_SUBDIRECTORY_NAME)
        for note_model in deck.metadata.models.values():
            note_model_directory = self._make_directory(note_models_directory, self.name_sanitizer(note_model.anki_dict["name"]))
            self._write_index_file(note_model_directory, NOTE_MODEL_FILE_NAME, note_model)

            self._write_file(note_model_directory, STYLE_FILE_NAME, STYLE_FILE_EXTENSION, note_model.anki_dict[CSS_FIELD_NAME])

            tmpls_directory = self._make_directory(note_model_directory, TMPLS_SUBDIRECTORY_NAME)
            for tmpl in note_model.anki_dict[TMPLS_FIELD_NAME]:
                tmpl_directory = self._make_directory(tmpls_directory, self.name_sanitizer(tmpl["name"]))

                self._write_file(tmpl_directory, FRONT_FILE_NAME, FRONT_FILE_EXTENSION, tmpl[QFMT_FIELD_NAME])
                self._write_file(tmpl_directory, BACK_FILE_NAME, BACK_FILE_EXTENSION, tmpl[AFMT_FIELD_NAME])

                tmpl = tmpl.copy()
                del tmpl[QFMT_FIELD_NAME], tmpl[AFMT_FIELD_NAME]
                self._write_index_file(tmpl_directory, TMPL_FILE_NAME, tmpl)
                

        self._save_changes(deck)

        if copy_media:
            self._copy_media(deck, deck_directory)

        return deck_directory

    def _make_directory(self, base_directory: Path, name):
        directory = base_directory.joinpath(name)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _write_index_file(self, directory: Path, name, object):
        content = json.dumps(object,
                             default=Serializable.default_json,
                             sort_keys=True,
                             indent=4,
                             ensure_ascii=False)
        self._write_file(directory, name, INDEX_FILE_EXTENSION, content)

    def _write_file(self, directory: Path, name, extention, content):
        with directory.joinpath(name).with_suffix(extention) \
                                         .open(mode='w', encoding="utf8") as file:
            file.write(content)

    def _save_changes(self, deck, is_export_child=False):
        """Save updates that were made during the export. E.g. UUID fields

        It saves decks, deck configurations and models.

        is_export_child refers to whether this deck is a child for the
        _purposes of the current export operation_.  For instance, if
        we're exporting or snapshotting a specific subdeck, then it's
        considered the "parent" here.  We need the argument to avoid
        duplicately saving deck configs and note models.

        """

        self.collection.decks.save(deck.anki_dict)
        for child_deck in deck.children:
            self._save_changes(child_deck, is_export_child=True)

        if not is_export_child:
            for deck_config in deck.metadata.deck_configs.values():
                self.collection.decks.save(deck_config.anki_dict)

            for model in deck.metadata.models.values():
                self.collection.models.save(model.anki_dict)

        # Notes?

    def _copy_media(self, deck, deck_directory):
        media_directory = deck_directory.joinpath(MEDIA_SUBDIRECTORY_NAME)

        media_directory.mkdir(parents=True, exist_ok=True)

        for file_src in deck.get_media_file_list():
            try:
                shutil.copy(os.path.join(self.collection.media.dir(), file_src),
                            str(media_directory.resolve()))
            except IOError as ioerror:
                print("Failed to copy a file {}. Full error: {}".format(file_src, ioerror))
