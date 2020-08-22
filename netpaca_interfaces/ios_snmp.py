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
This file contains the Cisco IOS interface collector that uses SNMP to obtain
the interface information required by the collectors.
"""

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List
import asyncio
import os

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import maya

from netpaca import Metric, MetricTimestamp
from netpaca.collectors.executor import CollectorExecutor
from netpaca.config_model import CollectorModel
from netpaca.drivers.ios_ssh import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

import netpaca_interfaces as interfaces

from netpaca_interfaces.aiosnmp.system import get_sys_uptime, get_snmpengine_uptime

import netpaca_interfaces.aiosnmp.interfaces as aio_snmp_ifs

# -----------------------------------------------------------------------------
# Exports (none)
# -----------------------------------------------------------------------------

__all__ = []

# -----------------------------------------------------------------------------
#
#                                   CODE BEGINS
#
# -----------------------------------------------------------------------------

_MAX_INT_UPTIME = 2 ** 32


# -----------------------------------------------------------------------------
#
#                 Register Cisco IOS to Interface Colletor
#
# -----------------------------------------------------------------------------


@interfaces.register
async def start(device: Device, executor: CollectorExecutor, spec: CollectorModel):
    """
    Start the interface collector process for Cisco IOS SSH devices, uses SNMPv2
    to obtain interface data that is needed by other collectors.

    Parameters
    ----------
    device:
        The device driver instance for the Cisco device

    executor:
        The executor that is used to start one or more collector tasks. In this
        instance, there is only one collector task started per device.

    spec:
        The collector model instance that contains information about the
        collector; for example the collector configuration values.
    """
    device.log.info(f"{device.name}: Starting Cisco IOS interfaces collector")
    device.private["interfaces"] = {"event": asyncio.Event()}

    executor.start(
        # required args
        spec=spec,
        coro=get_interfaces,
        device=device,
        # kwargs to collector coroutine:
        config=spec.config,
    )


# -----------------------------------------------------------------------------
#
#                             Collector Coroutine
#
# -----------------------------------------------------------------------------


async def get_interfaces(
    device: Device, timestamp: MetricTimestamp, config  # noqa
) -> Optional[List[Metric]]:
    """
    This coroutine is used the collect the interface information via SNMP
    that we need in order to process the metrics.

    Parameters
    ----------
    device: Device
        instance of Cisco IOS SSH device

    timestamp: MetricTimestamp
        The current timestamp

    config:
        The collector configuration options
    """
    community = os.environ["SNMP_COMMUNITY"]
    sys_uptime = await get_sys_uptime(device=device, community=community)

    snmp_uptime = await get_snmpengine_uptime(device=device, community=community)

    dev_uptime_wrapped = ((snmp_uptime * 100) // _MAX_INT_UPTIME) if snmp_uptime else 0

    if dev_uptime_wrapped > 0:
        new_sys_uptime = sys_uptime + (dev_uptime_wrapped * _MAX_INT_UPTIME)
        device.log.warning(
            f"{device.name}: uptime {sys_uptime} wrapped {dev_uptime_wrapped} times, "
            f"correcting: {new_sys_uptime}"
        )
        sys_uptime = new_sys_uptime

    # storing the SNMP sysUpTime value for potential later use
    device.private["sys_uptime"] = sys_uptime
    device.private["sys_uptime_wrapped"] = dev_uptime_wrapped

    # colelct the SNMP tables that are needed for this collector

    if_tables = await asyncio.gather(
        aio_snmp_ifs.get_if_name_table(device, community),
        aio_snmp_ifs.get_if_alias_table(device, community),
        aio_snmp_ifs.get_if_operstatus_table(device, community),
        aio_snmp_ifs.get_if_lastchange_table(device, community),
    )

    if_table_keys = ["if_name", "if_desc", "if_link_up", "if_lastchange"]

    # transmultate the tables into a dictionary for use by the other collectors.

    interface_data = {
        rec["if_name"]: rec
        for if_data in zip(*map(dict.values, if_tables))
        for rec in [dict(zip(if_table_keys, if_data))]
    }

    device.private["interfaces"].update(
        {"ts": timestamp, "maya_ts": maya.now(), "data": interface_data}
    )

    # trigger the pending tasks to awake to process the data.
    device.private["interfaces"]["event"].set()

    # no metrics to export, so return None.
    return None
