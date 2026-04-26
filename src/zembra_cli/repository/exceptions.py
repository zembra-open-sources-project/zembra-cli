"""Repository exceptions."""


class RecordNotFoundError(LookupError):
    """Signal that a requested database record does not exist.

    Attributes:
        table: Database table where the lookup was attempted.
        record_id: Identifier used for the failed lookup.
    """

    def __init__(self, table: str, record_id: str) -> None:
        """Initialize the not-found error.

        Args:
            table: Database table where the lookup was attempted.
            record_id: Identifier used for the failed lookup.

        Returns:
            None.
        """
        self.table = table
        self.record_id = record_id
        super().__init__(f"{table} record not found: {record_id}")
