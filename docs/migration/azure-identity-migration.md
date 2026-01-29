# Azure Identity Migration Guide

## Overview

The Fabric CLI has been migrated from MSAL (Microsoft Authentication Library) to **Azure Identity** for authentication. This migration provides several benefits while maintaining the same user experience.

## Key Benefits

✅ **Windows Authentication Broker Support** - Seamless single sign-on (SSO) using Windows Account Manager (WAM) on Windows 10/11  
✅ **Simplified API** - Higher-level credential types that abstract MSAL complexity  
✅ **Better Cross-Platform Support** - Consistent behavior across Windows, macOS, and Linux  
✅ **Modern Architecture** - Built on top of MSAL with Microsoft's recommended approach  
✅ **Automatic Token Caching** - Platform-specific secure token storage (DPAPI on Windows, Keychain on macOS)

## What Changed

### For End Users

**No changes required!** The migration is transparent:

- All existing authentication methods continue to work:
  - Interactive browser login
  - Service principal (client secret)
  - Service principal (certificate)
  - Managed identity (system-assigned and user-assigned)
  - Federated token / Workload identity
- Cached credentials remain valid
- Command-line interface is unchanged
- Environment variables work the same way

### For Developers

#### Authentication Architecture

**Before (MSAL):**
```python
from msal import PublicClientApplication, ConfidentialClientApplication
from msal_extensions import PersistedTokenCache

app = PublicClientApplication(client_id, authority, token_cache=cache)
token = app.acquire_token_interactive(scopes=scopes)
access_token = token["access_token"]
```

**After (Azure Identity):**
```python
from azure.identity import InteractiveBrowserCredential

credential = InteractiveBrowserCredential(client_id, tenant_id)
token = credential.get_token(scope)
access_token = token.token
```

#### Credential Mapping

| Authentication Method | MSAL | Azure Identity |
|----------------------|------|----------------|
| Interactive Browser | `PublicClientApplication` + `acquire_token_interactive` | `InteractiveBrowserCredential` |
| Interactive Browser (Windows WAM) | `PublicClientApplication` + `enable_broker_on_windows=True` | `InteractiveBrowserBrokerCredential` |
| Client Secret | `ConfidentialClientApplication` + client secret | `ClientSecretCredential` |
| Certificate | `ConfidentialClientApplication` + cert | `CertificateCredential` |
| Managed Identity | `ManagedIdentityClient` | `ManagedIdentityCredential` |
| Federated Token | `ConfidentialClientApplication` + assertion | Temporary MSAL fallback* |

\* Azure Identity doesn't yet support federated tokens natively, so we maintain a small MSAL wrapper for this specific case.

## Windows Broker Support

### What is the Windows Authentication Broker?

The Windows Authentication Broker (WAM) is a Windows 10/11 feature that provides:

- **Single Sign-On (SSO)** - Use your Windows login seamlessly
- **Conditional Access support** - Better security policy enforcement
- **No browser popup** - Native Windows authentication UI
- **Cached credentials** - Faster subsequent logins

### Requirements

To use the Windows broker:

1. **Operating System**: Windows 10 (build 17763+) or Windows 11
2. **Package**: `azure-identity-broker` (automatically installed on Windows)
3. **User signed into Windows** with Microsoft account or Azure AD

### How It Works

When you run `fab auth login` on Windows, the CLI automatically:

1. Detects you're on Windows
2. Attempts to use the broker (`InteractiveBrowserBrokerCredential`)
3. Falls back to standard browser if broker unavailable
4. Shows a native Windows authentication dialog (instead of browser)

```python
# Automatically selected based on platform
if platform.system() == "Windows" and BROKER_AVAILABLE:
    credential = InteractiveBrowserBrokerCredential(...)  # WAM
else:
    credential = InteractiveBrowserCredential(...)  # Browser
```

### Troubleshooting Broker Issues

If you experience issues with WAM:

1. **Verify Windows version**: Run `winver` - must be build 17763 or higher
2. **Check package**: Ensure `azure-identity-broker` is installed
3. **Sign into Windows**: You must be signed into Windows with a Microsoft/Azure AD account
4. **Review logs**: Enable debug mode with `--debug` flag

The CLI will automatically fall back to browser-based authentication if the broker fails.

## Token Caching

Azure Identity handles token caching automatically with platform-specific secure storage:

| Platform | Storage Mechanism | Encryption |
|----------|------------------|------------|
| Windows | Data Protection API (DPAPI) | ✅ Encrypted |
| macOS | Keychain | ✅ Encrypted |
| Linux | Secret Service (libsecret) or plaintext | ⚠️ Conditional |

### Linux Note

On Linux, encrypted caching requires `libsecret`. If unavailable, the CLI can fall back to plaintext caching if you enable it:

```bash
fab config set encryption_fallback_enabled true
```

**Security Warning**: Only enable plaintext caching in trusted environments.

## Migration Timeline

This change was introduced in version `[VERSION]` and is fully backward compatible.

## API Changes (Internal)

### Removed

- ❌ `msal_extensions` dependency (except for Windows non-broker scenarios)
- ❌ `FabAuth.app` attribute (replaced with `FabAuth._credential`)
- ❌ `FabAuth._get_app()` method (replaced with `FabAuth._get_credential()`)
- ❌ `FabAuth._get_persistence()` (replaced with `_get_cache_options()`)

### Added

- ✅ `FabAuth._credential` - Azure Identity credential instance
- ✅ `FabAuth._get_credential()` - Credential factory method
- ✅ `FabAuth._get_cache_options()` - Token cache configuration
- ✅ `FabAuth._get_token_with_federated_credential()` - MSAL fallback for workload identity

### Modified

- 🔄 `FabAuth.get_access_token()` - Now uses `credential.get_token()` instead of MSAL's `acquire_token_*` methods
- 🔄 `FabAuth.set_spn()` - Creates Azure Identity credentials instead of MSAL applications
- 🔄 `FabAuth.set_managed_identity()` - Uses `ManagedIdentityCredential`
- 🔄 `FabAuth._parse_certificate()` - Returns `pem_bytes` format for Azure Identity

## Testing

The migration includes comprehensive test coverage:

```bash
# Run auth tests
pytest tests/test_core/test_fab_auth.py -v

# Run all tests
pytest tests/ -v
```

## Support

### Common Issues

**Issue**: "Module 'azure.identity.broker' not found"  
**Solution**: The broker is only available on Windows. On other platforms, standard browser auth is used automatically.

**Issue**: "Token cache encryption failed"  
**Solution**: Enable fallback with `fab config set encryption_fallback_enabled true` (not recommended for production).

**Issue**: "Broker authentication failed"  
**Solution**: The CLI automatically falls back to browser. Check Windows version and ensure you're signed into Windows.

### Getting Help

- 📖 [Authentication Documentation](../examples/auth_examples.md)
- 🐛 [Report Issues](https://github.com/microsoft/fabric-cli/issues)
- 💬 [Discussions](https://github.com/microsoft/fabric-cli/discussions)

## References

- [Azure Identity Library](https://learn.microsoft.com/python/api/overview/azure/identity-readme)
- [Azure Identity Broker](https://learn.microsoft.com/python/api/overview/azure/identity-readme#brokered-authentication)
- [Windows Account Manager](https://learn.microsoft.com/azure/active-directory/develop/scenario-desktop-acquire-token-wam)
- [MSAL Python](https://learn.microsoft.com/python/api/msal/)
