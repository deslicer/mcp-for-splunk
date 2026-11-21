"""Hidden CLI input that never falls back to echoed stdin."""

import getpass
import warnings


def read_hidden_input(prompt: str) -> str:
    """Abort if the terminal cannot hide input, rather than exposing a credential."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            return getpass.getpass(prompt)
    except getpass.GetPassWarning:
        raise ValueError("Hidden input requires an interactive terminal.") from None
