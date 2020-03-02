from typing import NewType

#: A string representing a network location, i.e. any str matching
#: the pattern stated in RFC1808 Section 2.1 - <user>:<password>@<host>:<port>.
#: Typically, we only require the netloc to match the following regex::
#:
#:      r"^((?P<credentials>(?P<user>\w+):(?P<pw>.+))@)?(?P<host>.+)(:(?P<port>\d+)?)$"
#:
#: Where the group `credentials` is optional, but the group `port` is required.
#: Note that the latter breaks with the RFC definition, which states that `port`
#: may be optional as well.
#: The reason for this is that the Raiden Executable requires netlocs to include
#: a port number.
NetlocWithPort = NewType("NetlocWithPort", str)
