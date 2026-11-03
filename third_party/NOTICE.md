# Third-party attribution

The generic demonstration circuits are newly written textbook constructions. No
claim of a new XOR, inverter, or latch topology is made. The transmission-gate XOR
is the Boolean multiplexer construction `A ? not B : B` with ordinary CMOS devices.

The file `ngspice-47-local-node.patch` modifies `CKTdltNNum` in ngspice 47. That file
retains upstream's copyright: Copyright 1992 Regents of the University of California.
The patch uses the existing guard that permits deletion only beyond the saved
device-local node boundary, and begins the lookup at that boundary. The release
includes measurements for its tested circuits, not a proof for every simulator path.

Upstream source:
https://sourceforge.net/p/ngspice/ngspice/ci/ngspice-47/tree/src/spicelib/analysis/cktdltn.c

Read-only source mirror used for the reproducible source archive:
https://github.com/imr/ngspice/tree/ngspice-47

Upstream licensing: https://github.com/imr/ngspice/blob/ngspice-47/COPYING
The applicable modified-BSD notice is retained in `NGSPICE-LICENSE.txt`. ngspice
itself contains components under additional licenses; this package redistributes
no ngspice binaries or full source tree. Obtain and build it under its own notices.

The internal circuit-design research also checked compact XOR/XNOR candidates
against existing literature, including Scott T. Becker's *Circuitry and layouts for
XOR and XNOR logic*, US8653857B2, published 18 February 2014:
https://patents.google.com/patent/US8653857B2/en
This is background attribution. The public verification examples do not reproduce
the private search records or claim those existing designs as inventions.
