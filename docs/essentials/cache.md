# Caching

The Fabric CLI provides two types of caching for better experience and security:

## Token Caching

Tokens are managed via Microsoft Authentication Library (MSAL) extensions. By default, tokens are securely encrypted and stored in the user's home directory under `.config/fab/cache.bin`. The platforms that support encryption are: Windows, MacOS, and Linux. Maintain caution when handling or sharing this file, especially on systems without encryption support.

### Platform-specific requirements

| Platform | Encryption Backend | Requirements |
|----------|-------------------|--------------|
| Windows  | DPAPI            | Built-in, no additional setup |
| macOS    | Keychain         | Built-in, no additional setup |
| Linux    | libsecret        | Requires `libsecret` and a Secret Service provider (e.g., GNOME Keyring) |

!!! info "Linux users"
    On Linux, encrypted token caching requires the `libsecret` library and a running Secret Service daemon (such as GNOME Keyring). If these are not available, you may encounter an `EncryptionFailed` error. See [Troubleshooting](../troubleshooting.md#linux-installing-libsecret-for-encrypted-token-storage) for installation instructions.

## HTTP Response Caching

Certain endpoints are cached by default to diminish network traffic and improve overall responsiveness.

You can disable this feature by running (the default value is `true`):

```
fab config set cache_enabled false
```

To clear cached HTTP responses, run:

```
fab config clear-cache
```
