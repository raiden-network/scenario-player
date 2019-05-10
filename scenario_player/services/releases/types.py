from typing import Dict, Union

RaidenBinaryInfo = Dict[str, Union[str, None]]
RaidenArchiveInfo = Dict[str, Union[str, None]]
RaidenReleaseInfo = Dict[str, Union[RaidenArchiveInfo, RaidenBinaryInfo]]
