# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2019-2020, Science and Technology Facilities Council.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# -----------------------------------------------------------------------------
# Authors R. W. Ford, A. R. Porter and S. Siso, STFC Daresbury Lab
# -----------------------------------------------------------------------------

''' This module contains the datatype definitions.'''

from enum import Enum


class DataType(object):
    '''Base class from which all types are derived.'''

    def copy(self):
        '''Create a new instance of this type with the same properties as the
        current instance.

        '''
        return DataType()


class DeferredType(DataType):
    '''Indicates that the type is unknown at this point.'''

    def copy(self):
        '''Create a new instance of this type with the same properties as the
        current instance.

        '''
        return DeferredType()


class ScalarType(DataType):
    '''Describes a scalar datatype (and its precision).

    :param name: the name of this scalar type.
    :type name: :py:class:`pyclone.psyir.datatypes.ScalarType.Name`
    :param precision: the precision of this scalar type.
    :type precision: :py:class:`psyclone.psyir.datatypes.ScalarType.Precision`

    :raises TypeError: if the arguments are of the wrong type.

    '''

    class Name(Enum):
        '''Enumeration of the different scalar datatypes that are supported
        by the PSyIR.

        '''
        INTEGER = 1
        REAL = 2
        BOOLEAN = 3
        CHARACTER = 4

    class Precision(Enum):
        '''Enumeration of the different types of 'default' precision that may
        be specified for a scalar datatype.

        '''
        SINGLE = 1
        DOUBLE = 2

    def __init__(self, name, precision):
        from psyclone.psyir.symbols.datasymbol import DataSymbol
        if not isinstance(name, ScalarType.Name):
            raise TypeError(
                "ScalarType expected 'name' argument to be of type "
                "ScalarType.Name but found '{0}'."
                "".format(type(name).__name__))
        if not isinstance(precision, (int, ScalarType.Precision, DataSymbol)):
            raise TypeError(
                "ScalarType expected 'precision' argument to be of type "
                "int, ScalarType.Precision or DataSymbol, but found '{0}'."
                "".format(type(precision).__name__))
        if isinstance(precision, int) and precision <= 0:
            raise ValueError(
                "The precision of a DataSymbol when specified as an "
                "integer number of bytes must be > 0 but found '{0}'."
                "".format(precision))
        if (isinstance(precision, DataSymbol) and
                not (isinstance(precision.datatype, ScalarType) and
                     precision.datatype.name == ScalarType.Name.INTEGER) and
                not (isinstance(precision.datatype, DeferredType))):
            raise ValueError(
                "A DataSymbol representing the precision of another "
                "DataSymbol must be of either 'deferred' or scalar, "
                "integer type but got: {0}".format(str(precision)))

        self.name = name
        self.precision = precision

    def __str__(self):
        '''Construct a text representation of this scalar datatype.

        :returns: description of this scalar datatype.
        :rtype: str

        '''
        return ("{0}, {1}".format(self.name, self.precision))

    def copy(self):
        '''Create a new instance of this type with the same properties as the
        current instance.

        '''
        return ScalarType(self.name, self.precision)


class ArrayType(DataType):
    '''Describes an array datatype.

    :param datatype: the datatype of the array elements.
    :type datatype: :py:class:`psyclone.psyir.datatypes.DataType`
    :param shape: the shape of the array.
    :type shape: list of int ...

    :raises TypeError: if the arguments are of the wrong type.

    '''
    class Extent(Enum):
        '''
        Enumeration of array shape extents that are unspecified at compile
        time. When the extent must exist and is accessible via the run-time
        system it is an 'ATTRIBUTE'. When it may or may not be defined in the
        current scope (e.g. the array may need to be allocated/malloc'd) it
        is 'DEFERRED'.
        '''
        DEFERRED = 1
        ATTRIBUTE = 2

    def __init__(self, datatype, shape):

        if not isinstance(datatype, DataType):
            raise TypeError(
                "ArrayType expected 'datatype' argument to be of type "
                "DataType but found '{0}'."
                "".format(type(datatype).__name__))
        if not isinstance(shape, list):
            raise TypeError(
                "ArrayType expected 'shape' argument to be of type "
                "list but found '{0}'."
                "".format(type(shape).__name__))

        # TBD
        #for dimension in shape:
        #    if isinstance(dimension, DataSymbol):
        #        if dimension.datatype != DataType.INTEGER or dimension.shape:
        #            raise TypeError(
        #                "DataSymbols that are part of another symbol shape can"
        #                " only be scalar integers, but found '{0}'."
        #                "".format(str(dimension)))
        #    elif not isinstance(dimension, (self.Extent, int)):
        #        raise TypeError(
        #            "DataSymbol shape list elements can only be "
        #            "'DataSymbol', 'integer' or DataSymbol.Extent.")
        #self._shape = shape

        self.shape = shape
        self.name = datatype.name
        self.precision = datatype.precision
        self._datatype = datatype

    def __str__(self):
        '''Construct a text representation of this array datatype.

        :returns: description of this array datatype.
        :rtype: str

        '''
        from psyclone.psyir.symbols import DataSymbol
        dims = []
        for dimension in self.shape:
            if isinstance(dimension, DataSymbol):
                dims.append(dimension.name)
            elif isinstance(dimension, int):
                dims.append(str(dimension))
            elif isinstance(dimension, ArrayType.Extent):
                dims.append("'{0}'".format(dimension.name))
            else:
                raise InternalError(
                    "DataSymbol shape list elements can only be "
                    "'DataSymbol', 'integer' or 'None', but found '{0}'."
                    "".format(type(dimension)))
        return ("{0}, {1}, shape=[{2}]".format(self.name, self.precision,
                                               ", ".join(dims)))

        return ArrayType(self.datatype, self.shape)

    def copy(self):
        '''Create a new instance of this type with the same properties as the
        current instance.

        '''        
        return ArrayType(self._datatype.copy(), self.shape[:])


# Create common scalar datatypes
REAL_SINGLE_TYPE = ScalarType(ScalarType.Name.REAL,
                              ScalarType.Precision.SINGLE)
REAL_DOUBLE_TYPE = ScalarType(ScalarType.Name.REAL,
                              ScalarType.Precision.DOUBLE)
REAL4_TYPE = ScalarType(ScalarType.Name.REAL, 4)
REAL8_TYPE = ScalarType(ScalarType.Name.REAL, 8)
INTEGER_SINGLE_TYPE = ScalarType(ScalarType.Name.INTEGER,
                              ScalarType.Precision.SINGLE)
INTEGER_DOUBLE_TYPE = ScalarType(ScalarType.Name.INTEGER,
                              ScalarType.Precision.DOUBLE)
INTEGER4_TYPE = ScalarType(ScalarType.Name.INTEGER, 4)
INTEGER8_TYPE = ScalarType(ScalarType.Name.INTEGER, 8)
BOOLEAN_SINGLE_TYPE = ScalarType(ScalarType.Name.BOOLEAN,
                              ScalarType.Precision.SINGLE)
BOOLEAN_DOUBLE_TYPE = ScalarType(ScalarType.Name.BOOLEAN,
                              ScalarType.Precision.DOUBLE)
BOOLEAN4_TYPE = ScalarType(ScalarType.Name.BOOLEAN, 4)
BOOLEAN8_TYPE = ScalarType(ScalarType.Name.BOOLEAN, 8)
CHARACTER1_TYPE = ScalarType(ScalarType.Name.CHARACTER, 1)

#class StructureType(DataType):
#    ''' xxx '''
#
#    def __init__(self, datatypes):
#
#        if not isinstance(datatypes, list):
#            raise TypeError("XXX")
#        for datatype in datatypes:
#            if not isinstance(datatype, DataType):
#                raise TypeError("XXX")
#
#        self._datatypes = datatypes


#1 Sergi's implementation suggestion
#integer_type = IntegerType(precision)
#integer_one = Literal("1", integer_type)
#integer_two = Literal("2", integer_type)

# Mapping from PSyIR scalar data types to intrinsic Python types
# ignoring precision.
TYPE_MAP_TO_PYTHON = {ScalarType.Name.INTEGER: int,
                      ScalarType.Name.CHARACTER: str,
                      ScalarType.Name.BOOLEAN: bool,
                      ScalarType.Name.REAL: float}
