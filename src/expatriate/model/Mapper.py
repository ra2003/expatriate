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

import logging

logger = logging.getLogger(__name__)

class Mapper(object):
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __str__(self):
        return self.__class__.__name__ + ' ' + str(self._kwargs)

    def initialize(self, model):
        raise NotImplementedError

    def matches(self, child):
        raise NotImplementedError

    def parse_in(self, model, child):
        raise NotImplementedError

    def validate(self, model):
        raise NotImplementedError

    def produce_in(self, el, model):
        raise NotImplementedError
