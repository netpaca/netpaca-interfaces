#  Copyright (C) 2020  Jeremy Schulman
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This file contains asyncio SNMPv2 functions that can be used DeviceBase
instance.

References
----------
With regards to handling the SNMP ifLastChnage OID to determine
interface uptime:
https://github.com/netdisco/netdisco/issues/742#issuecomment-678491450
"""

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netpaca.drivers import DriverBase

from pysnmp.hlapi.asyncio import (
    SnmpEngine,
    ObjectType,
    ObjectIdentity,
    nextCmd,
    CommunityData,
    UdpTransportTarget,
    ContextData,
)

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["walk_table"]

# -----------------------------------------------------------------------------
#
#                                   CODE BEGINS
#
# -----------------------------------------------------------------------------


SNMP_V2_PORT = 161


async def walk_table(device: DriverBase, oid, community, factory=None):
    target = device.device_host
    snmp_engine = SnmpEngine()
    snmp_community = CommunityData(community)

    initial_var_binds = var_binds = [ObjectType(ObjectIdentity(oid))]
    collected = list()

    # if a factory function is not provided, then return the oid value

    if not factory:

        def factory(_vb):
            return _vb[1].prettyPrint()

    while True:

        (err_indications, err_st, err_idx, var_bind_table) = await nextCmd(
            snmp_engine,
            snmp_community,
            UdpTransportTarget((target, SNMP_V2_PORT)),
            ContextData(),
            *var_binds,
        )

        if err_indications:
            # an error indication is reason to raise an exception and stop
            # processing the walk
            emsg = f"{device.name}: SNMP failed on OID: {oid}"
            device.log.error(emsg)
            raise RuntimeError(emsg, err_indications)

        elif err_st:
            # an error status is reason to log the error, but continue walking
            # the MIB table.
            emsg = "%s at %s" % (
                err_st.prettyPrint(),
                err_idx and var_binds[int(err_idx) - 1][0] or "?",
            )
            device.log.error(emsg)

        for var_bind_row in var_bind_table:
            for idx, var_bind in enumerate(var_bind_row):
                if not initial_var_binds[0][idx].isPrefixOf(var_bind[0]):
                    return collected

                collected.append(factory(var_bind))

        # setup to fetch the next item in table
        var_binds = var_bind_table[-1]
