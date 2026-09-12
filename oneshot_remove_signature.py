#!/usr/bin/env python3
"""One-off: honour a signatory's request to have their row removed.

Runs from main, immediately before update-letter.py. Deletes AT MOST ONE Airtable
record. Never raises and always exits 0, so it cannot break the publish pipeline.

This file is temporary. Once a run logs "RESULT=not_found" the record is gone, and
this script, its workflow step, and the withdrawn_name_hashes filter in update-letter.py
can all be deleted.
"""

import hashlib
import json
import os
import sys
import traceback
import urllib.error
import urllib.request

from dotenv import load_dotenv
from pyairtable import Api

# The signatory who asked to be removed, held as SHA-256 of their 'Full name'
# stripped and lowercased, so this repository need not carry the name of someone
# who asked to be taken out of it. To check this digest against a name:
#
#   python -c "import hashlib; print(hashlib.sha256('<name>'.strip().lower().encode()).hexdigest())"
#
# If it does not select exactly one record, nothing is deleted (see main()). It is
# not one of update-letter.py's top_names, so the ordering logic there is unaffected.
TARGET_NAME_SHA256 = "623cf9af0142763d462eafda08237a5a97258fafa255819c707ddb4b8e324744"

# Ignore anything signed after this script was written, so that a future signatory
# who happens to share the name can never be matched. Airtable's createdTime is an
# ISO-8601 string, which compares correctly as text.
CREATED_BEFORE = "2026-09-12"

WHOAMI_URL = "https://api.airtable.com/v0/meta/whoami"


def name_digest(value):
    return hashlib.sha256((value or "").strip().lower().encode("utf-8")).hexdigest()


def log(message):
    print(f"oneshot: {message}", flush=True)


def report_scopes(api_key):
    """Print only the token's scopes.

    Never the id or email that whoami also returns -- these logs are world-readable.
    """
    request = urllib.request.Request(
        WHOAMI_URL, headers={"Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            scopes = json.loads(response.read().decode("utf-8")).get("scopes")
        log(f"scopes={sorted(scopes) if scopes else 'unknown (not reported)'}")
    except urllib.error.HTTPError as exc:
        log(f"scopes=unknown (whoami returned HTTP {exc.code})")
    except Exception as exc:
        log(f"scopes=unknown ({type(exc).__name__})")


def main():
    load_dotenv()
    api_key = os.environ["AIR_TABLE_API_KEY"]
    report_scopes(api_key)

    table = Api(api_key).table(
        os.environ["AIR_TABLE_BASE_ID"], os.environ["AIR_TABLE_NAME"]
    )
    records = table.all()

    matches = [
        record for record in records
        if name_digest(record["fields"].get("Full name")) == TARGET_NAME_SHA256
        and record.get("createdTime", "") < CREATED_BEFORE
    ]

    log(f"scanned {len(records)} records; matches={len(matches)}")

    if not matches:
        log("RESULT=not_found (nothing to delete; this script can now be removed)")
        return

    # Only ever delete when the digest identifies a single record. Refusing is the
    # safe direction: the filter in update-letter.py already keeps every copy off
    # the page, so nothing is published either way.
    if len(matches) > 1:
        log(f"RESULT=refused_ambiguous ({len(matches)} records share this name; "
            "deleting nothing)")
        return

    record_id = matches[0]["id"]

    try:
        table.delete(record_id)  # the only write operation in this repository
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (401, 403):
            log(
                f"RESULT=write_forbidden (HTTP {status}; the Airtable token cannot "
                "write. The filter in update-letter.py still keeps the signature "
                "off the page, so the letter is unaffected.)"
            )
            return
        raise

    log(f"RESULT=deleted {record_id}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        log("RESULT=error (publish pipeline continues unaffected)")
    sys.exit(0)
