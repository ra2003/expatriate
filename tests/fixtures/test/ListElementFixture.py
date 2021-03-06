# Copyright 2016 Casey Jaymes

# This file is part of Expatriate.
#
# Expatriate is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Expatriate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Expatriate.  If not, see <http://www.gnu.org/licenses/>.

from expatriate.model import *

from .EnclosedFixture import EnclosedFixture


@element(local_name='list_nil', list='list_nil', nillable=True, cls=EnclosedFixture, min=0)
@element(local_name='list_type', list='list_type', type=DecimalType, min=0)
@element(local_name='list_class', list='list_class', cls=EnclosedFixture, min=0)
class ListElementFixture(Model):
    pass
