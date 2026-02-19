"""Credential manager — encrypts and stores database passwords securely.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) from the
``cryptography`` package.  A machine-derived key is generated once and
stored alongside the encrypted credentials in a ``.credentials`` JSON
file in the project root.

Typical flow
------------
1. First run: user is prompted for a password, it gets encrypted and
   saved to ``.credentials``.
2. Subsequent runs: the saved password is decrypted transparently —
   no prompt needed.
3. ``--reset-password`` CLI flag deletes the saved credentials and
   re-prompts.
"""

import base64
import getpass
import hashlib
import json
import logging
import platform
import uuid
from pathlib import Path
from typing import Optional

from rich.console import Console

logger = logging.getLogger(__name__)
_console = Console(stderr=True)

# Default location for the credentials file
CREDENTIALS_FILE = Path(".credentials")


def _derive_machine_key() -> bytes:
    """Derive a deterministic Fernet key from machine-specific attributes.

    Combines the hostname, platform, and MAC address to produce a
    reproducible 32-byte key (URL-safe base64-encoded) that stays the
    same across runs on this machine but differs between machines.

    Returns:
        A 32-byte URL-safe base64-encoded Fernet key.
    """
    raw = f"{platform.node()}-{platform.system()}-{uuid.getnode()}"
    digest = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet():
    """Return a Fernet instance using the machine-derived key."""
    from cryptography.fernet import Fernet

    return Fernet(_derive_machine_key())


def encrypt_value(plain_text: str) -> str:
    """Encrypt a plain-text string and return a base64-encoded token.

    Args:
        plain_text: The secret to encrypt.

    Returns:
        Encrypted token as a string.
    """
    fernet = _get_fernet()
    return fernet.encrypt(plain_text.encode()).decode()


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token back to plain text.

    Args:
        token: The encrypted token.

    Returns:
        Original plain-text string.

    Raises:
        cryptography.fernet.InvalidToken: If the token is invalid or
        was encrypted on a different machine.
    """
    fernet = _get_fernet()
    return fernet.decrypt(token.encode()).decode()


def save_credential(key: str, plain_text: str, path: Path = CREDENTIALS_FILE) -> None:
    """Encrypt and persist a credential to the credentials file.

    If the file already exists, the new key is merged into it.

    Args:
        key: Identifier for the credential (e.g. ``pg_password``).
        plain_text: The secret value.
        path: Path to the credentials JSON file.
    """
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}

    data[key] = encrypt_value(plain_text)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Credential '%s' saved to %s", key, path)


def load_credential(key: str, path: Path = CREDENTIALS_FILE) -> Optional[str]:
    """Load and decrypt a credential from the credentials file.

    Args:
        key: Identifier for the credential.
        path: Path to the credentials JSON file.

    Returns:
        Decrypted plain-text string, or ``None`` if not found or
        decryption fails.
    """
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    token = data.get(key)
    if not token:
        return None

    try:
        return decrypt_value(token)
    except Exception:
        logger.warning(
            "Failed to decrypt credential '%s'. It may have been "
            "encrypted on a different machine.",
            key,
        )
        return None


def delete_credentials(path: Path = CREDENTIALS_FILE) -> None:
    """Delete the credentials file.

    Args:
        path: Path to the credentials JSON file.
    """
    if path.exists():
        path.unlink()
        logger.info("Credentials file deleted: %s", path)


def prompt_and_save_password(
    db_type: str,
    label: str = "Database",
) -> str:
    """Prompt the user for a database password, encrypt and save it.

    Args:
        db_type: Database type key used for storage
                 (``pg_password`` or ``mssql_password``).
        label: Human-readable label shown in the prompt.

    Returns:
        The plain-text password entered by the user, or empty string
        if skipped.
    """
    credential_key = f"{db_type}_password"

    # Try loading existing saved credential first
    saved = load_credential(credential_key)
    if saved is not None:
        _console.print(
            f"[green]Using saved {label} password from .credentials file.[/green]"
        )
        return saved

    # Prompt interactively
    _console.print(
        f"\n[bold yellow]{label} password required.[/bold yellow]"
    )

    password = getpass.getpass(f"Enter {label} password (hidden): ").strip()

    if not password:
        _console.print(
            "[yellow]No password entered. Proceeding with empty password.[/yellow]\n"
        )
        return ""

    # Offer to save encrypted
    _console.print()
    save = input(
        "Save password (encrypted) for future use? [Y/n]: "
    ).strip().lower()

    if save in ("", "y", "yes"):
        try:
            save_credential(credential_key, password)
            _console.print(
                "[green]Password encrypted and saved to .credentials "
                "— you won't be asked again.[/green]\n"
            )
        except ImportError:
            _console.print(
                "[red]cryptography package not installed. "
                "Install with: pip install cryptography[/red]\n"
                "[yellow]Password will not be saved.[/yellow]\n"
            )
    else:
        _console.print(
            "[dim]Password not saved. You'll be prompted again next time.[/dim]\n"
        )

    return password
