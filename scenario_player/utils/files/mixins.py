from scenario_player.utils.files.parsing import parse_architecture, parse_platform, parse_version


class VersionedMixin:
    """Supply a `version` property to the class it's mixed into.

    Requires a :attr:`.path` attribute on the class.
    """

    @property
    def version(self) -> str:
        return parse_version(self.path)


class PlatformSpecificMixin:
    """Supply a `platform` property to the class it's mixed into.

    Requires a :attr:`.path` attribute on the class.
    """

    @property
    def platform(self) -> str:
        return parse_platform(self.path)


class ArchitectureSpecificMixin:
    """Supply an `architecture` property to the class it's mixed into.

    Requires a :attr:`.path` attribute on the class.
    """

    @property
    def architecture(self) -> str:
        return parse_architecture(self.path)
