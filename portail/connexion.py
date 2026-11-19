#!/usr/bin/env python3
"""Appelé par le DHCP à chaque appareil qui reçoit une adresse."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journal import journal_dhcp

if __name__ == "__main__":
    journal_dhcp(sys.argv)
