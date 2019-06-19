class CannotImplicitlyChangeFileType(FileExistsError):
    """We tried to replace an existing symlink with a new hard-copy or an existing hard-copy with a new symlink.

    By default, the interface prevents this, even if an `overwrite` parameter was given.

    The existing symlink or hard-copy must first be removed explicitly.
    """
