# 3. Licensing: dual AGPL-3.0-only / GPL-3.0-or-later

- Status: accepted
- Date: 2026-10-13

## Context

The contributed code should be reusable under a copyleft license while leaving
the recipient free to prefer either the network-oriented AGPL or the more
permissive "or later" GPL grant.

## Decision

The project is dual-licensed. A recipient may use it under **either**:

1. GNU Affero General Public License, version 3 only (text in `agpl-3.0.txt`),
   or
2. GNU General Public License, version 3 or any later version (text in
   `gpl-3.0.txt`).

`COPYING` records the choice; `package.json` expresses it as the SPDX
`(AGPL-3.0-only OR GPL-3.0-or-later)`.

## Consequences

- The AGPL option omits the "or later version" clause; the GPL option omits the
  "at your option" clause.
- Both options carry an additional permission under AGPL-3.0 §7 / GPL-3.0 §7
  permitting combination with the Sensoray SDK core; see
  [0006](0006-binary-redistribution.md).
- The licenses cover this project's own code only. The Sensoray SDK core in
  `src/common/` retains its own upstream copyright and is not licensed here; see
  [0005](0005-upstream-inclusion-not-licensing.md).
- Downstream users must comply with the chosen license; the Sensoray SDK core in
  `src/common/` retains its own upstream licensing terms.
