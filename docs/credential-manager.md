# Credential Manager

**Module:** `sql_analyzer/credential_manager.py`

Handles secure storage and retrieval of database passwords using Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) from the `cryptography` package.

## How It Works

```
First run (no saved password):
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Password Prompt  │───▶│   Encrypt    │───▶│ .credentials    │
│ (hidden input)   │    │ (Fernet AES) │    │ (JSON file)     │
└─────────────────┘    └──────────────┘    └─────────────────┘

Subsequent runs:
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ .credentials    │───▶│   Decrypt    │───▶│ Plain password   │
│ (JSON file)     │    │ (Fernet AES) │    │ (in memory only) │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## Encryption Details

### Key Derivation

The encryption key is **machine-derived** — not stored anywhere:

```python
raw = f"{platform.node()}-{platform.system()}-{uuid.getnode()}"
digest = hashlib.sha256(raw.encode()).digest()
key = base64.urlsafe_b64encode(digest)  # 32-byte Fernet key
```

This means:
- The key is deterministic on the same machine (same hostname, OS, MAC address)
- The `.credentials` file cannot be decrypted on a different machine
- No master password is needed

### Algorithm

- **Fernet** from the `cryptography` package
- Internally uses AES-128-CBC encryption + HMAC-SHA256 authentication
- Each encrypted token includes a timestamp for optional expiry checks

## Storage Format

The `.credentials` file is a JSON object where each key is a credential identifier and each value is an encrypted Fernet token:

```json
{
  "pg_password": "gAAAAABn...(encrypted)...",
  "mssql_password": "gAAAAABn...(encrypted)..."
}
```

The file is gitignored by default. It should **never** be committed to version control.

## Functions

### `encrypt_value(plain_text) → str`

Encrypts a plain-text string using the machine-derived Fernet key.

### `decrypt_value(token) → str`

Decrypts a Fernet token back to plain text. Raises `cryptography.fernet.InvalidToken` if the token was encrypted on a different machine.

### `save_credential(key, plain_text, path=CREDENTIALS_FILE)`

Encrypts and persists a credential to the `.credentials` JSON file. Merges with existing credentials if the file already exists.

### `load_credential(key, path=CREDENTIALS_FILE) → Optional[str]`

Loads and decrypts a credential. Returns `None` if not found, file doesn't exist, or decryption fails (e.g. different machine).

### `delete_credentials(path=CREDENTIALS_FILE)`

Deletes the entire `.credentials` file. Used by `--reset-password`.

### `prompt_and_save_password(db_type, label) → str`

The main entry point used by `build_configs()` in `sql_analyzer.py`:

1. Tries to load an existing saved credential
2. If found → returns it (no prompt)
3. If not found → prompts with `getpass.getpass()` (hidden input)
4. Asks if the user wants to save it encrypted
5. Returns the plain-text password

**Parameters:**
- `db_type`: Key prefix for storage — `"pg"` → `"pg_password"`, `"mssql"` → `"mssql_password"`
- `label`: Human-readable name shown in the prompt (e.g. `"PostgreSQL"`)

## Integration with CLI

### Password Resolution Order

```
--pg-password CLI arg  >  PG_PASSWORD env var / .env  >  .credentials  >  interactive prompt
```

### `--reset-password` Flag

When specified, `delete_credentials()` is called before any password resolution. This forces re-prompting even if a `.credentials` file exists.

## Security Notes

1. **Machine-bound** — encrypted passwords only work on the machine where they were created
2. **Not a vault** — this is convenience encryption, not a secrets manager. For production deployments, use proper secret management (e.g., HashiCorp Vault, AWS Secrets Manager)
3. **File permissions** — on multi-user systems, restrict `.credentials` to the current user (`chmod 600` on Linux/macOS)
4. **Memory** — decrypted passwords exist in process memory during execution. This is unavoidable for any database connection
