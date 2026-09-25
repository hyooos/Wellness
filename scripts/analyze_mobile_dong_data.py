"""Deprecated compatibility entry point for the four-site analysis.

The integrated four-site analysis now builds the mobility detail outputs too.
"""

from __future__ import annotations

from analyze_four_sites_by_designation import main


if __name__ == "__main__":
    main()
