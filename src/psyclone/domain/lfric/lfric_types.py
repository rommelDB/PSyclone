# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2023, Science and Technology Facilities Council.
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
# Author J. Henrichs, Bureau of Meteorology

'''This module contains a singleton class that manages LFRic types. '''


from collections import namedtuple

from psyclone.domain.lfric import LFRicConstants
from psyclone.psyir.nodes import Literal
from psyclone.psyir.symbols import (ArrayType, ContainerSymbol, DataSymbol,
                                    ImportInterface, INTEGER_TYPE, ScalarType)


class LFRicTypes:
    '''This class implements a singleton that manages LFRic types.
    Using the 'call' interface, you can query the data type for
    LFRic types, e.g.:
    lfric_types = LFRicTypes()
    rvfdds = lfric_types("RealVectorFieldDataDataSymbol")

    '''

    # Class variable to store the singleton instance
    _instance = None

    # ------------------------------------------------------------------------
    def __new__(cls):
        '''Implement a singleton - only one instance will ever be created.

        :returns: the singleton instance of LFRicTypes.
        :rtype: :py:class:`psyclone.domain.lfric.LFRicTypes`

        '''
        if LFRicTypes._instance is None:
            # Return a new instance. The constructor will set _instance
            # in this case
            return super().__new__(cls)

        # Return the existing instance, in which case the constructor will
        # not re-initialise the internal data structures
        return LFRicTypes._instance

    # ------------------------------------------------------------------------
    def __init__(self):

        # Test if this is returning the existing instance, if so, skip
        # initialisation
        if self == LFRicTypes._instance:
            return

        # First time __init__ is called, initialise all data structures.
        LFRicTypes._instance = self

        self._name_to_class = {}

        self._create_modules()
        self._create_generic_scalars()
        self._create_lfric_dimension()
        self._create_specific_scalars()
        self._create_fields()
        # Generate LFRic vector-field-data symbols as subclasses of
        # field-data symbols
        for intrinsic in ["Real", "Integer", "Logical"]:
            name = f"{intrinsic}VectorFieldDataDataSymbol"
            baseclass = self(f"{intrinsic}FieldDataDataSymbol")
            self._name_to_class[name] = type(name, (baseclass, ), {})

    # ------------------------------------------------------------------------
    def __call__(self, name):
        ''':returns: the class of the required type.
        :rtype:  Class instance

        '''
        return self._name_to_class[name]

    # ------------------------------------------------------------------------
    def _create_modules(self):
        # The first Module namedtuple argument specifies the name of the
        # module and the second argument declares the name(s) of any symbols
        # declared by the module.
        Module = namedtuple('Module', ["name", "vars"])
        modules = [
            Module(LFRicConstants().UTILITIES_MOD_MAP["constants"]["module"],
                   ["i_def", "r_def", "r_solver", "r_tran", "l_def"])]

        # Generate LFRic module symbols from definitions
        for module_info in modules:
            module_name = module_info.name.upper()
            # Create the module (using a PSyIR ContainerSymbol)
            self._name_to_class[module_name] = \
                ContainerSymbol(module_info.name)
            # Create the variables specified by the module (using
            # PSyIR DataSymbols)
            for module_var in module_info.vars:
                var_name = module_var.upper()
                self._name_to_class[var_name] = \
                    DataSymbol(module_var, INTEGER_TYPE,
                               interface=ImportInterface(self(module_name)))

    # ------------------------------------------------------------------------
    def _create_generic_scalars(self):
        GenericScalar = namedtuple('GenericScalar', ["name", "intrinsic",
                                                     "precision"])
        generic_scalar_datatypes = [
            GenericScalar("LfricIntegerScalar", ScalarType.Intrinsic.INTEGER,
                          self("I_DEF")),
            GenericScalar("LfricRealScalar", ScalarType.Intrinsic.REAL,
                          self("R_DEF")),
            GenericScalar("LfricLogicalScalar", ScalarType.Intrinsic.BOOLEAN,
                          self("L_DEF"))]

        # Generate generic LFRic scalar datatypes and symbols from definitions
        for info in generic_scalar_datatypes:

            # Create the generic data
            type_name = f"{info.name}DataType"
            self._create_generic_scalar_data_type(type_name,
                                                  info.intrinsic,
                                                  info.precision)
            type_class = self(type_name)
            # Create the generic data symbol
            symbol_name = f"{info.name}DataSymbol"
            self._create_generic_scalar_data_symbol(symbol_name, type_class)

    # ------------------------------------------------------------------------
    def _create_generic_scalar_data_type(self, name, intrinsic, precision):

        def __my_generic_scalar_type_init__(self, precision=None):
            if not precision:
                precision = self.default_precision
            ScalarType.__init__(self, self.intrinsic, precision)

        self._name_to_class[name] = \
            type(name, (ScalarType, ),
                 {"__init__": __my_generic_scalar_type_init__,
                  "intrinsic": intrinsic,
                  "default_precision": precision})

    # ------------------------------------------------------------------------
    def _create_generic_scalar_data_symbol(self, name, type_class):

        def __my_generic_scalar_symbol_init__(self, name, precision=None,
                                              **kwargs):
            DataSymbol.__init__(self, name,
                                self.type_class(precision=precision),
                                **kwargs)
        self._name_to_class[name] = \
            type(name, (DataSymbol, ),
                 {"__init__": __my_generic_scalar_symbol_init__,
                  "type_class": type_class})

    # ------------------------------------------------------------------------
    def _create_lfric_dimension(self):

        class LfricDimension(Literal):
            '''An LFRic-specific scalar integer that captures a literal array
            dimension which can either have the value 1 or 3. This is used for
            one of the dimensions in basis and differential basis
            functions.

            :param str value: the value of the scalar integer.

            :raises nodes import Literal
            :raises ValueError: if the supplied value is not '1 or '3'.

            '''
            # pylint: disable=undefined-variable
            def __init__(self, value):
                super().__init__(value,
                                 LFRicTypes()("LfricIntegerScalarDataType")())
                if value not in ['1', '3']:
                    raise ValueError(f"An LFRic dimension object must be '1' "
                                     f"or '3', but found '{value}'.")
        # --------------------------------------------------------------------

        # Create the required entries in the dictionary
        self._name_to_class["LfricDimension"] = LfricDimension
        self._name_to_class["LFRIC_SCALAR_DIMENSION"] = LfricDimension("1")
        self._name_to_class["LFRIC_VECTOR_DIMENSION"] = LfricDimension("3")

    # ------------------------------------------------------------------------
    def _create_specific_scalars(self):
        # The Scalar namedtuple has 3 properties: the first
        # determines the names of the resultant datatype and datasymbol
        # classes, the second references the generic scalar type
        # classes declared above and the third specifies any
        # additional class properties that should be declared in the generated
        # datasymbol class.

        Scalar = namedtuple('Scalar', ["name", "generic_type_name",
                                       "properties"])
        specific_scalar_datatypes = [
            Scalar("CellPosition", "LfricIntegerScalarData", []),
            Scalar("MeshHeight", "LfricIntegerScalarData", []),
            Scalar("NumberOfCells", "LfricIntegerScalarData", []),
            Scalar("NumberOfDofs", "LfricIntegerScalarData", ["fs"]),
            Scalar("NumberOfUniqueDofs", "LfricIntegerScalarData", ["fs"]),
            Scalar("NumberOfFaces", "LfricIntegerScalarData", []),
            Scalar("NumberOfEdges", "LfricIntegerScalarData", []),
            Scalar("NumberOfQrPointsInXy", "LfricIntegerScalarData", []),
            Scalar("NumberOfQrPointsInZ", "LfricIntegerScalarData", []),
            Scalar("NumberOfQrPointsInFaces", "LfricIntegerScalarData", []),
            Scalar("NumberOfQrPointsInEdges", "LfricIntegerScalarData", [])]

        for info in specific_scalar_datatypes:
            type_name = f"{info.name}DataType"
            self._name_to_class[type_name] = \
                type(type_name, (self(f"{info.generic_type_name}Type"), ), {})

            symbol_name = f"{info.name}DataSymbol"
            base_class = self(f"{info.generic_type_name}Symbol")
            self._create_scalar_data_type(symbol_name, base_class,
                                          info.properties)

    # ------------------------------------------------------------------------
    def _create_scalar_data_type(self, class_name, base_class, properties):

        # ---------------------------------------------------------------------
        # This is the __init__ function for the newly declared scalar data
        # types, which will be added as an attribute for the newly created
        # class. It parses the additional positional and keyword arguments
        # and sets them as attributes.

        def __my_scalar_init__(self, name, *args, **kwargs):
            # Set all the positional arguments as attributes:
            for i, arg in enumerate(args):
                setattr(self, self.parameters[i], arg)
            # Now handle the keyword arguments: any keyword arguments
            # that are declared as parameter will be set as attribute,
            # anything else will be passed to the constructor of the
            # base class.
            remaining_kwargs = {}
            for key, value in kwargs.items():
                # It is one of the additional parameters, set it as
                # attribute:
                if key in self.parameters:
                    setattr(self, key, value)
                else:
                    # Otherwise add it as keyword parameter for the
                    # base class constructor
                    remaining_kwargs[key] = value
            self.base_class.__init__(self, name, **remaining_kwargs)

        # ----------------------------------------------------------------

        # Now create the actual class. We need to keep a copy of the parameters
        # of this class as attributes, otherwise they would be shared among the
        # several instances of the __myinit__function: this affects the
        # required arguments (array_type.properties) and scalar class:
        self._name_to_class[class_name] = \
            type(class_name, (base_class, ),
                 {"__init__": __my_scalar_init__,
                  "base_class": base_class,
                  "parameters": properties})

    # ------------------------------------------------------------------------
    def _create_fields(self):
        # Note, field_datatypes are no different to array_datatypes and are
        # treated in the same way. They are only separated into a different
        # list because they are used to create vector field datatypes and
        # symbols.

        # The Array namedtuple has 4 properties: the first determines the
        # names of the resultant datatype and datasymbol classes, the second
        # references the generic scalar type classes declared above, the third
        # specifies the dimensions of the array by specifying a list of scalar
        # type classes declared above, and the fourth specifies any additional
        # class properties that should be declared in the generated datasymbol
        # class.

        Array = namedtuple('Array',
                           ["name", "scalar_type", "dims", "properties"])
        field_datatypes = [
            Array("RealFieldData", "LfricRealScalarDataType",
                  ["number of unique dofs"], ["fs"]),
            Array("IntegerFieldData", "LfricIntegerScalarDataType",
                  ["number of unique dofs"], ["fs"]),
            Array("LogicalFieldData", "LfricLogicalScalarDataType",
                  ["number of unique dofs"], ["fs"])]

        # TBD: #918 the dimension datatypes and their ordering is captured in
        # field_datatypes and array_datatypes but is not stored in the
        # generated classes.

        # TBD: #926 attributes will be constrained to certain datatypes and
        # values. For example, a function space attribute should be a string
        # containing the name of a supported function space. These are not
        # currently checked.

        # TBD: #927 in some cases the values of attributes can be inferred, or
        # at least must be consistent. For example, a field datatype has an
        # associated function space attribute, its dimension symbol (if there
        # is one) must be a NumberOfUniqueDofsDataSymbol which also has a
        # function space attribute and the two function spaces must be
        # the same. This is not currently checked.
        array_datatypes = [
            Array("Operator", "LfricRealScalarDataType",
                  ["number of dofs", "number of dofs", "number of cells"],
                  ["fs_from", "fs_to"]),
            Array("DofMap", "LfricIntegerScalarDataType",
                  ["number of dofs"], ["fs"]),
            Array("BasisFunctionQrXyoz", "LfricRealScalarDataType",
                  [self("LfricDimension"), "number of dofs",
                   "number of qr points in xy",
                   "number of qr points in z"], ["fs"]),
            Array("BasisFunctionQrFace", "LfricRealScalarDataType",
                  [self("LfricDimension"), "number of dofs",
                   "number of qr points in faces",
                   "number of faces"], ["fs"]),
            Array("BasisFunctionQrEdge", "LfricRealScalarDataType",
                  [self("LfricDimension"), "number of dofs",
                   "number of qr points in edges",
                   "number of edges"], ["fs"]),
            Array("DiffBasisFunctionQrXyoz", "LfricRealScalarDataType",
                  [self("LfricDimension"), "number of dofs",
                   "number of qr points in xy",
                   "number of qr points in z"], ["fs"]),
            Array("DiffBasisFunctionQrFace", "LfricRealScalarDataType",
                  [self("LfricDimension"), "number of dofs",
                   "number of qr points in faces",
                   "number of faces"], ["fs"]),
            Array("DiffBasisFunctionQrEdge", "LfricRealScalarDataType",
                  [self("LfricDimension"), "number of dofs",
                   "number of qr points in edges", "number of edges"], ["fs"]),
            Array("QrWeightsInXy", "LfricRealScalarDataType",
                  ["number of qr points in xy"], []),
            Array("QrWeightsInZ", "LfricRealScalarDataType",
                  ["number of qr points in z"], []),
            Array("QrWeightsInFaces", "LfricRealScalarDataType",
                  ["number of qr points in faces"], []),
            Array("QrWeightsInEdges", "LfricRealScalarDataType",
                  ["number of qr points in edges"], [])
            ]

        for array_type in array_datatypes + field_datatypes:
            name = f"{array_type.name}DataType"
            self._create_array_data_type_class(name, len(array_type.dims),
                                               self(array_type.scalar_type))

            my__class = self(name)
            name = f"{array_type.name}DataSymbol"
            self._create_array_data_symbol_class(name, my__class,
                                                 array_type.properties)

    # ------------------------------------------------------------------------
    def _create_array_data_type_class(self, name, num_dims, scalar_type):

        # ---------------------------------------------------------------------
        # This is the __init__ function for the newly declared classes, which
        # will be added as an attribute for the newly created class. It parses
        # the additional positional and keyword arguments and sets them as
        # attributes.

        def __my_type_init__(self, dims):
            if len(dims) != self.num_dims:
                raise TypeError(f"'{type(self).__name__}' expected the number "
                                f"of supplied dimensions to be {self.num_dims}"
                                f" but found {len(dims)}.")
            ArrayType.__init__(self, self.scalar_class(), dims)

        # ---------------------------------------------------------------------
        self._name_to_class[name] = \
            type(name, (ArrayType, ),
                 {"__init__": __my_type_init__,
                  "scalar_class": scalar_type,
                  "num_dims": num_dims})

    # ------------------------------------------------------------------------
    def _create_array_data_symbol_class(self, name, scalar_type,
                                        array_properties):
        '''This function creates an array-data-symbol-class and adds it to
        the internal type dictionary.

        :param str name: the name of the class to be created.
        :param scalar_type: ??
        :param array_properties: the list of additional required properties \
            to be passed to the constructor.
        :type array_properties: List[str]

        '''

        # ---------------------------------------------------------------------
        # This is the __init__ function for the newly declared classes, which
        # will be added as an attribute for the newly created class. It parses
        # the additional positional and keyword arguments and sets them as
        # attributes.

        def __my_symbol_init__(self, name, dims, *args, **kwargs):
            # Set all the positional arguments as attributes:
            for i, arg in enumerate(args):
                setattr(self, self.parameters[i], arg)
            # Now handle the keyword arguments: any keyword arguments
            # that are declared as parameter will be set as attribute,
            # anything else will be passed to the constructor of the
            # base class.
            remaining_kwargs = {}
            for key, value in kwargs.items():
                # It is one of the additional parameters, set it as
                # attribute:
                if key in self.parameters:
                    setattr(self, key, value)
                else:
                    # Otherwise add it as keyword parameter for the
                    # base class constructor
                    remaining_kwargs[key] = value
            DataSymbol.__init__(self, name, self.scalar_class(dims),
                                **remaining_kwargs)
        # ----------------------------------------------------------------

        # Now create the actual class. We need to keep a copy of the parameters
        # of this class as attributes, otherwise they would be shared among the
        # several instances of the __myinit__function: this affects the
        # required arguments (array_type.properties) and scalar class:
        self._name_to_class[name] = \
            type(name, (DataSymbol, ),
                 {"__init__": __my_symbol_init__,
                  "scalar_class": scalar_type,
                  "parameters": array_properties})
