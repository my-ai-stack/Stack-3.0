import asyncio
import time
import logging
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BridgeResilience")

@dataclass
class RemoteCredentials:
    worker_jwt: str
    expires_in: int
    api_base_url: str
    worker_epoch: int

class FlushGate:
    """
    Queues writes while a critical operation (like history flush or transport rebuild)
    is in flight, ensuring order is preserved.
    """
    def __init__(self):
        self._active = False
        self._queue: List[Any] = []

    def start(self):
        self._active = True

    def enqueue(self, *messages) -> bool:
        if self._active:
            self._queue.extend(messages)
            return True
        return False

    def end(self) -> List[Any]:
        self._active = False
        msgs = self._queue[:]
        self._queue.clear()
        return msgs

    def drop(self):
        self._active = False
        self._queue.clear()

    @property
    def active(self) -> bool:
        return self._active

class BridgeResilienceLayer:
    def __init__(
        self,
        base_url: str,
        org_uuid: str,
        title: str,
        get_access_token: Callable[[], Optional[str]],
        on_auth_401: Optional[Callable[[str], asyncio.Future]] = None,
        http_timeout_ms: int = 30000,
        token_refresh_buffer_ms: int = 300000, # 5 mins
    ):
        self.base_url = base_url
        self.org_uuid = org_uuid
        self.title = title
        self.get_access_token = get_access_token
        self.on_auth_401 = on_auth_401
        self.http_timeout_ms = http_timeout_ms
        self.token_refresh_buffer_ms = token_refresh_buffer_ms

        self.session_id: Optional[str] = None
        self.credentials: Optional[RemoteCredentials] = None
        self.transport: Any = None # This will be the actual MCP transport

        self.flush_gate = FlushGate()
        self.auth_recovery_in_flight = False
        self.torn_down = False
        self.initial_flush_done = False

        self._refresh_task: Optional[asyncio.Task] = None

    async def initialize(self, transport_factory: Callable):
        """
        Initializes the session and sets up the transport.
        transport_factory should return a transport object that has connect(), close(),
        and write_batch() methods.
        """
        # 1. Create Session
        token = self.get_access_token()
        if not token:
            logger.error("[BridgeResilience] No OAuth token available")
            return False

        self.session_id = await self._create_code_session(token)
        if not self.session_id:
            return False

        # 2. Fetch Credentials
        creds = await self._fetch_remote_credentials(self.session_id, token)
        if not creds:
            return False

        self.credentials = creds

        # 3. Build Transport
        try:
            self.transport = transport_factory(
                session_url=f"{creds.api_base_url}/{self.session_id}",
                ingress_token=creds.worker_jwt,
                epoch=creds.worker_epoch,
            )
            await self.transport.connect()
        except Exception as e:
            logger.error(f"[BridgeResilience] Transport setup failed: {e}")
            return False

        # 4. Start Refresh Scheduler
        self._schedule_refresh(creds.expires_in)
        return True

    async def _create_code_session(self, token: str) -> Optional[str]:
        # Mock of POST /v1/code/sessions
        logger.info(f"[BridgeResilience] Creating code session with title {self.title}")
        # In real implementation: return response.json()['id']
        return "cse_mock_id_123"

    async def _fetch_remote_credentials(self, session_id: str, token: str) -> Optional[RemoteCredentials]:
        # Mock of POST /bridge
        logger.info(f"[BridgeResilience] Fetching credentials for session {session_id}")
        # In real implementation: fetch from /bridge
        return RemoteCredentials(
            worker_jwt="mock_worker_jwt",
            expires_in=3600,
            api_base_url="https://api.anthropic.com/v1/bridge",
            worker_epoch=1
        )

    def _schedule_refresh(self, expires_in_s: int):
        if self._refresh_task:
            self._refresh_task.cancel()

        delay = expires_in_s - (self.token_refresh_buffer_ms / 1000)
        self._refresh_task = asyncio.create_task(self._refresh_timer(delay))

    async def _refresh_timer(self, delay: float):
        try:
            await asyncio.sleep(max(0, delay))
            await self.recover_from_auth_failure("proactive_refresh")
        except asyncio.CancelledError:
            pass

    async def recover_from_auth_failure(self, cause: str):
        if self.auth_recovery_in_flight or self.torn_down:
            return

        self.auth_recovery_in_flight = True
        logger.info(f"[BridgeResilience] Recovery started. Cause: {cause}")

        try:
            stale_token = self.get_access_token()
            if self.on_auth_401 and stale_token:
                await self.on_auth_401(stale_token)

            token = self.get_access_token()
            if not token:
                raise Exception("No OAuth token after refresh")

            fresh_creds = await self._fetch_remote_credentials(self.session_id, token)
            if not fresh_creds:
                raise Exception("Failed to fetch fresh credentials")

            await self._rebuild_transport(fresh_creds)

        except Exception as e:
            logger.error(f"[BridgeResilience] Recovery failed: {e}")
        finally:
            self.auth_recovery_in_flight = False

    async def _rebuild_transport(self, fresh: RemoteCredentials):
        self.flush_gate.start()
        try:
            # Save sequence number if transport supports it
            seq = getattr(self.transport, 'last_sequence_num', 0)

            await self.transport.close()

            # Re-create transport (this would typically be passed via factory or handled by a manager)
            # For this implementation, we assume we can trigger a reconnect on the existing transport
            # or replace it.
            self.credentials = fresh
            await self.transport.reconnect(
                ingress_token=fresh.worker_jwt,
                epoch=fresh.worker_epoch,
                initial_sequence_num=seq
            )

            self._schedule_refresh(fresh.expires_in)
            self._drain_flush_gate()
        finally:
            self.flush_gate.drop()

    def _drain_flush_gate(self):
        msgs = self.flush_gate.end()
        if msgs and self.transport:
            self.transport.write_batch(msgs)

    async def write_messages(self, messages: List[Any]):
        if self.flush_gate.enqueue(*messages):
            logger.info(f"[BridgeResilience] Queued {len(messages)} messages")
            return

        if self.transport:
            self.transport.write_batch(messages)

    async def teardown(self):
        self.torn_down = True
        if self._refresh_task:
            self._refresh_task.cancel()
        self.flush_gate.drop()
        if self.transport:
            await self.transport.close()
