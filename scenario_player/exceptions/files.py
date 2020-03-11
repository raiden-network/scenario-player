class ReferenceDropped(UserWarning):
    """While updating references, we found a file that changed on disk and thusly dropped it."""

    def __init__(self, ref, attr):
        message = f"Reference {ref} changed on disk - dropping it from '{attr}'."
        super(ReferenceDropped, self).__init__(message)
