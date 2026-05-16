from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Awaitable, Generator, Optional

import streamlit as st
from loguru import logger


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    """
    Streamlit runs user code synchronously; we keep a dedicated event loop in session_state
    to avoid repeated loop creation and to avoid nested asyncio.run() issues.
    """
    loop: Optional[asyncio.AbstractEventLoop] = st.session_state.get("_async_loop")
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        st.session_state["_async_loop"] = loop
        logger.debug("Created Streamlit async event loop")
    return loop


def run_async(coro: Awaitable[Any]) -> Any:
    """
    Run an async coroutine from sync Streamlit code reliably.
    """
    try:
        loop = _get_or_create_loop()
        return loop.run_until_complete(coro)
    except RuntimeError as e:
        # Fallback if the stored loop is in a bad state or already running.
        logger.warning(f"Async runner fallback due to RuntimeError: {e}")
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def sync_stream(async_gen: AsyncGenerator[str, None]) -> Generator[str, None, None]:
    """
    Bridge an async generator into a sync generator for Streamlit write_stream.
    """
    loop = _get_or_create_loop()
    while True:
        try:
            chunk = loop.run_until_complete(async_gen.__anext__())
            yield chunk
        except StopAsyncIteration:
            break

