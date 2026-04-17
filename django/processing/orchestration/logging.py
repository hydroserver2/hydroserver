import logging
from contextvars import ContextVar

run_id_var: ContextVar[str] = ContextVar("run_id", default="-")


class RunIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        full = run_id_var.get()
        record.run_id = full[-8:] if len(full) > 8 else full

        return True
