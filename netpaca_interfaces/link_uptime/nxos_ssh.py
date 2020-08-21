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
Collector: Interface Optic Monitoring
Device: Cisco IOS via SSH

For details on the async SSH device driver, refer to the scrapli
project: https://github.com/carlmontanari/scrapli

"""
# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netpaca.collectors.executor import CollectorExecutor
from netpaca.drivers.nxos_ssh import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netpaca_interfaces import link_uptime
from netpaca_interfaces.link_uptime.nxapi import get_link_uptimes


# -----------------------------------------------------------------------------
# Exports (none)
# -----------------------------------------------------------------------------

__all__ = []


# -----------------------------------------------------------------------------
#
#                                CODE BEGINS
#
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
#
#                  Register Cisco Device SSH to Colletor Type
#
# -----------------------------------------------------------------------------


@link_uptime.register
async def start(
    device: Device, executor: CollectorExecutor, spec: link_uptime.CollectorModel
):
    """
    The IF DOM collector start coroutine for Cisco NXOS SSH devices.  The
    purpose of this coroutine is to start the collector task.  Nothing fancy.

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
    device.log.debug(f"{device.name}: Starting Cisco NX-OS SSH link flap collector")

    executor.start(
        # required args
        spec=spec,
        coro=get_link_uptimes,
        device=device,
        # kwargs to collector coroutine:
        config=spec.config,
    )
