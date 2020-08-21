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
This file implements the interfaces collector for Arista EAPI devices.
"""

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List
from asyncio import Event

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------
import maya

from netpaca import Metric, MetricTimestamp
from netpaca.collectors.executor import CollectorExecutor
from netpaca.drivers.eapi import Device
from netpaca.config_model import CollectorModel

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

import netpaca_interfaces as interfaces

# -----------------------------------------------------------------------------
# Exports (none)
# -----------------------------------------------------------------------------

__all__ = []

# -----------------------------------------------------------------------------
#
#                                   CODE BEGINS
#
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#
#                 Register Cisco Device NXAPI to Colletor Type
#
# -----------------------------------------------------------------------------


@interfaces.register
async def start(
    device: Device, executor: CollectorExecutor, spec: CollectorModel
):
    """
    The IF DOM collector start coroutine for Cisco NX-API enabled devices.  The
    purpose of this coroutine is to start the collector task.  Nothing fancy.

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
    device.log.info(f"{device.name}: Starting Arista EOS interfaces collector")

    device.private['interfaces'] = {
        'event': Event()
    }

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
    device: Device, timestamp: MetricTimestamp,
    config      # noqa
) -> Optional[List[Metric]]:
    """
    This coroutine will be executed as a asyncio Task on a periodic basis, the
    purpose is to collect data from the device and return the list Metrics.

    Parameters
    ----------
    device:
        The Cisco device driver instance for this device.

    timestamp: MetricTimestamp
        The current timestamp

    config:
        The collector configuration options

    Returns
    -------
    list of Metic items, or None
    """

    res = await device.eapi.exec(["show interfaces"])
    sh_iface = res[0]

    if not sh_iface.ok:
        device.log.error(f"{device.name}/{interfaces.name}: unable to obtain interface data, will try again.")
        return None

    # store the raw interfaces data into the private area of the device instance
    # so that it can be used by other collectors.  The method used here is just
    # a first trial; might use something different in the future.

    device.private['interfaces'].update({
        'ts': timestamp,
        'maya_ts': maya.now(),
        'data': sh_iface.output
    })

    # trigger the pending tasks to awake to process the data.
    device.private['interfaces']['event'].set()

    return None
