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

from netpaca import Metric, MetricTimestamp
from netpaca.collectors.executor import CollectorExecutor
from netpaca.drivers.eapi import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netpaca_ptp import ptp_master

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


@ptp_master.register
async def start(
    device: Device, executor: CollectorExecutor, spec: ptp_master.CollectorModel,
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
    device.log.info(f"{device.name}: Starting Arista EOS PTP master collector")
    executor.start(
        # required args
        spec=spec,
        coro=get_ptp_master,
        device=device,
        # kwargs to collector coroutine:
        config=spec.config,
    )


# -----------------------------------------------------------------------------
#
#                             Collector Coroutine
#
# -----------------------------------------------------------------------------


async def get_ptp_master(
    device: Device,
    timestamp: MetricTimestamp,  # noqa - not used
    config,  # noqa - not used
) -> Optional[List[Metric]]:
    """
    This coroutine is used to create the link uptime metrics for Arista EOS
    systems.

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

    cli_res, *_ = await device.eapi.exec(
        ['show ptp masters']
    )

    if not cli_res.ok:
        return None

    if not (ptp_par := cli_res.output.get('parent')):
        return None

    if not (gm_clk_qual := ptp_par.get('gmClockQuality')):
        return None

    return [ptp_master.PtpMasterClassMetric(ts=timestamp, value=gm_clk_qual['clockClass'])]
