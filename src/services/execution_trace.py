from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4


def document_snapshots(documents, metric="distance"):
    return [dict(id=doc.id, text=doc.text, metadata=deepcopy(doc.metadata),
                 rank=index, score=doc.score, metric=metric)
            for index, doc in enumerate(documents, 1)]


class TracedExecutionError(RuntimeError):
    def __init__(self, message, trace):
        super().__init__(message)
        self.trace = trace


class ExecutionTrace:
    def __init__(self, on_event=None):
        self.started = perf_counter()
        self.on_event = on_event
        self.data = dict(id=str(uuid4()), status="running", started_at=self.now(), steps=[])

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat()

    def snapshot(self):
        result = deepcopy(self.data)
        if result["status"] == "running":
            result["duration_ms"] = round((perf_counter() - self.started) * 1000)
        return result

    def emit(self):
        if self.on_event:
            self.on_event(self.snapshot())

    @contextmanager
    def step(self, kind, title, inputs=None):
        step = dict(id=str(len(self.data["steps"]) + 1), kind=kind, title=title,
                    status="running", started_at=self.now(), input=inputs or {}, output={})
        self.data["steps"].append(step)
        started = perf_counter()
        self.emit()
        try:
            yield step
        except Exception as error:
            step["status"] = "failed"
            step["error"] = str(error)
            raise
        else:
            if step["status"] == "running":
                step["status"] = "completed"
        finally:
            step["completed_at"] = self.now()
            step["duration_ms"] = round((perf_counter() - started) * 1000)
            self.emit()

    def finish(self, status="completed", error=None):
        self.data.update(status=status, completed_at=self.now(),
                         duration_ms=round((perf_counter() - self.started) * 1000))
        if error:
            self.data["error"] = error
        self.emit()
        return self.snapshot()
