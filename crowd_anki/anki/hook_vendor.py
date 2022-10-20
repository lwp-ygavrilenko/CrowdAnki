from aqt import gui_hooks

from dataclasses import field, dataclass
from pathlib import Path
from typing import Any

from ..config.config_settings import ConfigSettings
from ..anki.adapters.hook_manager import AnkiHookManager
from ..anki.ui.utils import progress_indicator
from ..export.anki_exporter_wrapper import exporters_hook
from ..importer.anki_importer import AnkiImporter
from ..history.archiver_vendor import ArchiverVendor
from ..utils.deckconf import disambiguate_crowdanki_uuid
from ..utils.notifier import Notifier, AnkiTooltipNotifier


@dataclass
class HookVendor:
    window: Any
    config: ConfigSettings
    hook_manager: AnkiHookManager = AnkiHookManager()
    notifier: Notifier = field(default_factory=AnkiTooltipNotifier)

    def setup_hooks(self):
        self.setup_exporter_hook()
        self.setup_snapshot_hooks()
        self.setup_add_config_hook()
        self.setup_import_hook()

    def setup_exporter_hook(self):
        self.hook_manager.hook("exportersList", exporters_hook)

    def setup_snapshot_hooks(self):
        snapshot_handler = ArchiverVendor(self.window, self.config).snapshot_on_sync
        self.hook_manager.hook('profileLoaded', snapshot_handler)
        self.hook_manager.hook('unloadProfile', snapshot_handler)

    def setup_add_config_hook(self):
        gui_hooks.deck_conf_did_add_config.append(disambiguate_crowdanki_uuid)

    def setup_import_hook(self):
        def import_handler():
            if self.config.automated_snapshot:
                with progress_indicator(self.window, 'Importing CrowdAnki representation of all decks'):
                    for deck_path in filter(Path.is_dir, self.config.full_snapshot_path.iterdir()):
                        AnkiImporter.import_deck_from_path(self.window.col, deck_path, True)
                    self.notifier.info("Import successful",
                                f"The CrowdAnki import from {str(self.config.full_snapshot_path)} successfully completed")
        self.hook_manager.hook('profileLoaded', import_handler)
