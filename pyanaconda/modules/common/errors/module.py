#
# DBus errors related to modules.
#
# Copyright (C) 2019  Red Hat, Inc.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from pyanaconda.core.dbus import dbus_error
from pyanaconda.modules.common.constants.namespaces import ANACONDA_NAMESPACE
from pyanaconda.modules.common.errors.general import AnacondaError


@dbus_error("UnavailableModuleError", namespace=ANACONDA_NAMESPACE)
class UnavailableModuleError(AnacondaError):
    """The DBus module is not available."""
    pass
