class CannotImplicitlyChangeFileType(FileExistsError):
    """We tried to replace an existing symlink with a new hard-copy or vice versa.

    By default, the interface prevents this, even if an `overwrite` parameter was given.

    The existing symlink or hard-copy must first be removed explicitly.
    """


class ReferenceDropped(UserWarning):
    """While updating references, we found a file that changed on disk and thusly dropped it."""

    def __init__(self, ref, attr):
        message = f"Reference {ref} changed on disk - dropping it from '{attr}'."
        super(ReferenceDropped, self).__init__(message)
