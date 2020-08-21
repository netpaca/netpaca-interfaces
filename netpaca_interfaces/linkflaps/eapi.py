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


# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, List

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------
import maya
from netpaca import Metric, MetricTimestamp
from netpaca.collectors.executor import CollectorExecutor
from netpaca.drivers.eapi import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netpaca_interfaces import linkflaps

# -----------------------------------------------------------------------------
# Exports (none)
# -----------------------------------------------------------------------------

__all__ = []


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#
#                     Register Arista Device to Colletor Type
#
# -----------------------------------------------------------------------------


@linkflaps.register
async def start(
    device: Device, executor: CollectorExecutor, spec: linkflaps.CollectorModel,
):
    """
    The IF DOM collector start coroutine for Arista EOS devices.  The purpose of this
    coroutine is to start the collector task.  Nothing fancy.

    Parameters
    ----------
    device:
        The device driver instance for the Arista device

    executor:
        The executor that is used to start one or more collector tasks. In this
        instance, there is only one collector task started per device.

    spec:
        The collector model instance that contains information about the
        collector; for example the collector configuration values.
    """
    device.log.info(f"{device.name}: Starting Arista EOS link flaps collector")
    executor.start(
        # required args
        spec=spec,
        coro=get_link_flaps,
        device=device,
        # kwargs to collector coroutine:
        config=spec.config,
    )


# -----------------------------------------------------------------------------
#
#                             Collector Coroutine
#
# -----------------------------------------------------------------------------


async def get_link_flaps(
    device: Device,
    timestamp: MetricTimestamp,  # noqa - not used
    config,  # noqa - not used
) -> Optional[List[Metric]]:
    """
    This coroutine is used to create the link uptime metrics for Arista EOS
    systems.  Only interfaces that are link-up are included in the metrics
    collection.

    Parameters
    ----------
    device:
        The Arisa EOS device driver instance for this device.

    timestamp: MetricTimestamp
        The timestamp now in milliseconds

    config:
        The collector configuration options

    """

    # wait for the interfaces collector to indicate that the data is available
    # for processing.

    interfaces = device.private["interfaces"]
    await interfaces["event"].wait()

    eos_data = interfaces["data"]["interfaces"]
    ifs_ts = interfaces["ts"]
    maya_now = interfaces["maya_ts"]

    metrics = list()

    for if_name, if_data in eos_data.items():

        # skip interfaces that are not link-up
        if if_data["interfaceStatus"] != "connected":
            continue

        # EOS stores the value as an epoc timestamp (float).  We need to convert
        # this to uptime in minutes.

        last_flapped = if_data["lastStatusChangeTimestamp"]
        dt = maya.MayaDT(epoch=last_flapped)
        uptime_min = (maya_now - dt).total_seconds() // 60

        # add metric tags for interface name and description

        tags = dict(if_name=if_name, if_desc=if_data["description"])

        # create the link uptime metric using the timestamp when the interfaces
        # where collected.

        metrics.append(
            linkflaps.LinkUptimeMetric(value=uptime_min, ts=ifs_ts, tags=tags)
        )

    return metrics
