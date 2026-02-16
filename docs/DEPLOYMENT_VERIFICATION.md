# Deployment Verification Report

**Date:** February 16, 2026  
**Verified by:** Automated checksum comparison

## Summary

✅ **VERIFIED: Deployed version matches local version exactly**

## Deployed Image Details

| Property | Value |
|----------|-------|
| Image Registry | `asia-south1-docker.pkg.dev/sticky-net-485205/cloud-run-source-deploy/sticky-net` |
| Digest | `sha256:94f2a8582aa5ee4ab92dcd40a75db2493464cd3edd4004b7346c68d16781356f` |
| Created | February 6, 2026 00:07:20 UTC |
| Active Revision | `sticky-net-00014-htr` |
| Deployed | February 5, 2026 18:37:33 UTC |

## File-by-File Checksum Comparison

All 20 Python source files have identical MD5 checksums between deployed image and local code:

| File | MD5 Checksum | Match |
|------|--------------|-------|
| `src/__init__.py` | `44b6b00e46a221e04c3ff9b1aee91d62` | ✓ |
| `src/main.py` | `284c0ff982cb1873bb5fbd0b3c25ef46` | ✓ |
| `src/exceptions.py` | `cd2d55602f3dff2b71599ff12b3b4d3f` | ✓ |
| `src/api/__init__.py` | `81c0cbf54529511097fb606c3cb30c2b` | ✓ |
| `src/api/routes.py` | `db25394e381c3ed70b231493be08da35` | ✓ |
| `src/api/callback.py` | `771b519d2941d9ef3673339a5971b5cf` | ✓ |
| `src/api/schemas.py` | `f920eee13e3834fba3df0b09a8984e7e` | ✓ |
| `src/api/middleware.py` | `b5381b9d7e5f986097fb7de7cd60779c` | ✓ |
| `src/agents/__init__.py` | `1d12cccb77c9353fb483a0fe4fae7371` | ✓ |
| `src/agents/honeypot_agent.py` | `5befba9facb827d81b637fed3b68a2d6` | ✓ |
| `src/agents/prompts.py` | `6bfa921fb8f94e0bc8558dc72dd6c341` | ✓ |
| `src/agents/persona.py` | `55e19fe37bf2b1d68002b4006ff821a5` | ✓ |
| `src/agents/policy.py` | `70eef8ff56ef86c0b1df286bb2a605d0` | ✓ |
| `src/agents/fake_data.py` | `4d915ea19f62c074253d548ad21ecd2e` | ✓ |
| `src/detection/__init__.py` | `02d11dcd25685fa2ee1c224c25f6fbba` | ✓ |
| `src/detection/classifier.py` | `c19bdae2355e46ec47a7b32df60b6e38` | ✓ |
| `src/detection/detector.py` | `efb021747e6894d09ab91c5f79cee06c` | ✓ |
| `src/intelligence/__init__.py` | `03eeb690ad0f5a589b6b43f14375031d` | ✓ |
| `src/intelligence/extractor.py` | `7884304a19c06e8aa2ee212894fcd9a6` | ✓ |
| `src/intelligence/validators.py` | `fc6728449c938059174e8202a27856f9` | ✓ |

## Verification Method

1. Pulled the deployed Docker image from Artifact Registry
2. Extracted MD5 checksums of all Python files inside the container
3. Computed MD5 checksums of local source files
4. Ran `diff` on both checksum lists

```bash
# Commands used:
docker pull asia-south1-docker.pkg.dev/sticky-net-485205/cloud-run-source-deploy/sticky-net@sha256:94f2a8582aa5ee4ab92dcd40a75db2493464cd3edd4004b7346c68d16781356f

docker run --rm --platform linux/amd64 <image> find /app/src -name "*.py" -exec md5sum {} \; | sort > deployed_checksums.txt

find src -name "*.py" -exec md5 -r {} \; | sort > local_checksums.txt

diff deployed_checksums.txt local_checksums.txt
# Result: No differences
```

## Conclusion

The Cloud Run deployment is running the exact same code as the local repository.
