#!/usr/bin/python
# -*- coding: utf-8 -*-
# **********************************************************************
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
#   02111-1307, USA.
#
#   (c)2012 - X Engineering Software Systems Corp. (www.xess.com)
# **********************************************************************

"""
Base object for performing USB I/O between XESS board and host PC.
"""

import logging
from xsjtag import *

DEFAULT_XSUSB_ID = 0
DEFAULT_MODULE_ID = 255


class XsHostIo:

    """Base object for performing USB I/O between XESS board and host PC."""

    USER1_INSTR = XsBitarray('000010'[::-1])
    USER2_INSTR = XsBitarray('000011'[::-1])

    def __init__(
        self,
        xsusb_id=DEFAULT_XSUSB_ID,
        module_id=DEFAULT_MODULE_ID,
        xsjtag=None,
        ):
        """Setup the parameters for the USB I/O link between the PC and the XESS board."""

        self._xsusb_id = xsusb_id
        if isinstance(module_id, int):
            self.module_id = XsBitarray.from_int(module_id, 8)
        else:
            self.module_id = XsBitarray(module_id)
        if xsjtag == None:
            self._xsusb = XsUsb(xsusb_id)
            self.xsjtag = XsJtag(self._xsusb)
        else:
            self.xsjtag = xsjtag
        self.user_instr = self.USER1_INSTR
        self.initialize()

    def initialize(self):
        """Initialize the USB I/O link."""

        assert self.xsjtag != None
        self.xsjtag.reset_tap()  # Reset TAP FSM to test-logic-reset state.
        # Send TAP FSM to the shift-ir state.
        self.xsjtag.go_thru_tap_states('Run-Test/Idle', 'Select-DR-Scan'
                , 'Select-IR-Scan', 'Capture-IR', 'Shift-IR')
        # Now enter the USER1 JTAG instruction into the IR and go to the update-ir state.
        self.xsjtag.shift_tdi(tdi=self.user_instr, do_exit_shift=True)
        # USER instruction is now active, so transfer to the shift-dr state where
        # data transfers will occur.
        self.xsjtag.go_thru_tap_states('Update-IR', 'Select-DR-Scan',
                'Capture-DR', 'Shift-DR')
        self.xsjtag.flush()

    def reset(self):
        """Reset the USB I/O link."""

        self.initialize()

    def send_rcv(self, payload, num_result_bits):
        """Send a bit array payload and then return a results bit array with num_result_bits."""

        logging.debug('Send ' + str(payload.length()) + 'bits. Receive '
                       + str(num_result_bits) + ' bits.')

        # Create the TDI bit array by concatenating the module ID, number of bits in the payload, and the payload bits.
        tdi_bits = XsBitarray()
        tdi_bits.extend(self.module_id)
        num_payload_bits = XsBitarray.from_int(payload.length()
                + num_result_bits, 32)
        tdi_bits.extend(num_payload_bits)
        tdi_bits.extend(payload)

        logging.debug('Module ID = ' + repr(self.module_id))
        logging.debug('# payload bits = ' + repr(num_payload_bits))
        logging.debug('payload = ' + repr(payload))
        logging.debug('# TDI bits = ' + str(tdi_bits.length()))
        logging.debug('TDI = ' + repr(tdi_bits))

        # Send the TDI bits.
        self.xsjtag.shift_tdi(tdi=tdi_bits)
        self.xsjtag.flush()
        # Get the result bits from TDO.
        tdo_bits = self.xsjtag.shift_tdo(num_result_bits)
        return tdo_bits


