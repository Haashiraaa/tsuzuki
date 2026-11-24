"""The threads that run downloads, one per slot."""

import logging
import threading

from tsuzuki.storage import claim_next, connect, recover_interrupted
from tsuzuki.worker.job import Services, WorkerSettings, run_episode

log = logging.getLogger("tsuzuki.worker")

STOP_WAIT_SECONDS = 15.0


class WorkerPool:
    def __init__(self, settings: WorkerSettings, services: Services) -> None:
        self._settings = settings
        self._services = services
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        """Put episodes cut off by an earlier crash back in the queue, then start the slots.
        The database must already be migrated."""
        conn = connect(self._settings.database)
        try:
            recovered = recover_interrupted(conn, self._services.clock())
        finally:
            conn.close()
        if recovered:
            log.info("Put %d interrupted download(s) back in the queue", recovered)
        for number in range(self._settings.slots):
            thread = threading.Thread(
                target=self._work, name=f"tsuzuki-slot-{number + 1}", daemon=True
            )
            thread.start()
            self._threads.append(thread)

    def stop(self, timeout: float = STOP_WAIT_SECONDS) -> None:
        """Ask the slots to stop. A running download puts itself back in the queue and resumes
        next time, so stopping is quick but never loses an episode."""
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout)

    def _work(self) -> None:
        conn = connect(self._settings.database)
        try:
            while not self._stop.is_set():
                record = claim_next(conn, self._services.clock(), self._settings.retention)
                if record is None:
                    self._stop.wait(self._settings.poll_seconds)
                    continue
                run_episode(conn, record, self._settings, self._services, self._stop.is_set)
        except Exception:
            log.exception("A download slot stopped unexpectedly")
        finally:
            conn.close()
