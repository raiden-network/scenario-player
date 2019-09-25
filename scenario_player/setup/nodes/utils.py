import pathlib
import random

from typing import Optional

from eth_utils import encode_hex

from scenario_player.utils.files.base import ManagedFile
from scenario_player.utils.files.mixins import VersionedMixin, ArchitectureSpecificMixin, PlatformSpecificMixin


class RaidenExecutable(ManagedFile, ArchitectureSpecificMixin, PlatformSpecificMixin, VersionedMixin):
    """A :class:`.ManagedFile` sublcass, taking care of downloading and extracting a Raiden Binary Archive."""
    @classmethod
    def download(cls, version: str, tar_dir: pathlib.Path, source: Optional[str] = None) -> ManagedFile:
        """Download the binary archive from the raiden cloud.

        :raises ArchiveNotFound: if we cannot find a downloadable archive for the specified version.
        """

    def unpack(self) -> ManagedFile:
        """Extract the binary archive at this instance's :attr:`pathlib.Path.parent`."""


def create_keystore(*, run_number: int, index: int, scenario_name: str, password: str) -> pathlib.Path:
    """Create a new keystore.

    The private key is a combination of the local seed, the run number, the instance's index,
    and the scenario name, hashed using sha256.

    It stores the keystore in a file on disk as a JSON-encoded UTF-8 string.

    The file name is always `<checksum of eth_address>.keystore`.

    FIXME: Keystore files are currently always created on a scenario run. This
        is a necessary evil, since raiden currently has no backwards compatibility
        mechanism in place. This means, keystores are not compatible between
        tested raiden versions. It also stops us from testing scenarios run
        on a non-fresh aka 'used' token econonmy.
    """


def get_local_seed(base_path: pathlib.Path) -> str:
    """Return a persistent random seed value.

    We need a unique seed per scenario player 'installation'.
    This is used in the node private key generation to prevent re-use of node keys between
    multiple users of the scenario player.

    The seed is a byte sequence of length 20, randomly chosen, and hex-encoded.

    The seed is stored in a file inside the ``.base_path``.
    """
    seed_file = base_path.joinpath("seed.txt")
    if not seed_file.exists():
        seed = encode_hex(bytes(random.randint(0, 255) for _ in range(20)))
        seed_file.write_text(seed)
    else:
        seed = seed_file.read_text().strip()
    return seed
