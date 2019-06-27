class CorruptedDBEntry(Exception):
    """We treid calling :func:``json.dumps`` on a string fetched from the database,
     but the operation resulted in a decodeing error."""

    def __init__(self, table, key):
        message = f"Database entry in table {table} at key {key} is not JSON-encoded or corrupted!"
        super(CorruptedDBEntry, self).__init__(message)
