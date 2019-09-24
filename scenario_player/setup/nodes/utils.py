import pathlib
from typing import Optional
from scenario_player.utils.files.base import ManagedFile
from scenario_player.utils.files.mixins import VersionedMixin, ArchitectureSpecificMixin, PlatformSpecificMixin


class RaidenExecutable(ManagedFile, ArchitectureSpecificMixin, PlatformSpecificMixin, VersionedMixin):
    """A :class:`.ManagedFile` sublcass, taking care of downloading and extracting a Raiden Binary Archive."""
    def download(self, source: Optional[str] = None) -> None:
        """Download the binary archive from the raiden cloud.

        :raises ArchiveNotFound: if we cannot find a downloadable archive for the specified version.
        """
        pass

    def unpack(self) -> ManagedFile:
        """Extract the binary archive at this instance's :attr:`pathlib.Path.parent`."""


def create_keystore(*, run_number: int, index: int, scenario_name: str, password: str) -> pathlib.Path:
    """Create a new keystore.

    The private key is a combination of the run number, the instance's index, and the
    scenario name, hashed using sha256.

    It stores the keystore in a file on disk as a JSON-encoded UTF-8 string.

    The file name is always `<checksum of eth_address>.keystore`.

    FIXME: Keystore files are currently always created on a scenario run. This
        is a necessary evil, since raiden currently has no backwards compatibility
        mechanism in place. This means, keystores are not compatible between
        tested raiden versions. It also stops us from testing scenarios run
        on a non-fresh aka 'used' token econonmy.
    """
