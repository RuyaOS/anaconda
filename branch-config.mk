# Makefile include for branch specific configuration settings
#
# Copyright (C) 2020  Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Store a branch specific configuration here to avoid dealing with
# conflicts on multiple places.


# Name of the expected current git branch.
# This could be master, fXX-devel, fXX-release, rhelX-branch, rhel-X ...
GIT_BRANCH ?= f36-release

# Directory for this anaconda branch in anaconda-l10n repository. This could be master, fXX, rhel-8 etc.
L10N_DIR ?= f36

# Base container for our containers.
BASE_CONTAINER ?= registry.fedoraproject.org/fedora:36

# COPR repo for use in container builds.
# Can be @rhinstaller/Anaconda for master, or @rhinstaller/Anaconda-devel for branched Fedora.
COPR_REPO ?= \@rhinstaller/Anaconda-devel
