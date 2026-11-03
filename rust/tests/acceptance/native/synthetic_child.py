# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Synthetic subprocess adversaries; no product, provider or credential access."""

import os
import sys
import time

if sys.argv[1] == "wait":
    time.sleep(30)
elif sys.argv[1] == "flood":
    os.write(1, b"x" * (64 * 1024 + 1))
elif sys.argv[1] == "secret":
    print("synthetic-secret-must-not-be-in-receipt")
elif sys.argv[1] == "empty-tests":
    print("test result: ok. 0 passed; 0 failed; 0 ignored; 1 filtered out")
elif sys.argv[1] == "cursor-flood":
    import tty

    tty.setraw(0)
    os.write(1, b"$ ")
    while True:
        os.write(1, b"\x1b[6n" * 1024)
else:
    raise SystemExit(2)
