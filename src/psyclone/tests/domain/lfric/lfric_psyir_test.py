# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Science and Technology Facilities Council.
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
# Author R. W. Ford, STFC Daresbury Lab
# Modified S. Siso, STFC Daresbury Lab
# Modified J. Henrichs, Bureau of Meteorology

'''Test that the LFRic-specific PSyIR classes are created and declared
correctly'''

import pytest

from psyclone.domain.lfric import psyir as lfric_psyir, LFRicTypes
from psyclone.psyir.symbols import ContainerSymbol, DataSymbol, \
    ImportInterface, ScalarType, LocalInterface, ArgumentInterface, \
    ArrayType, Symbol
from psyclone.psyir.nodes import Reference, Literal


# Modules and their arguments
@pytest.mark.parametrize("module, symbol_list",
                         [(lfric_psyir.CONSTANTS_MOD,
                           [lfric_psyir.I_DEF, lfric_psyir.R_DEF,
                            lfric_psyir.L_DEF])])
def test_constants_mod(module, symbol_list):
    '''Test the generated module symbol and its argument symbols are
    created correctly.

    '''
    assert isinstance(module, ContainerSymbol)
    for symbol in symbol_list:
        assert isinstance(symbol, DataSymbol)
        assert isinstance(symbol.interface, ImportInterface)
        assert symbol.interface.container_symbol is module


# Generic scalars
@pytest.mark.parametrize("data_type_name, symbol_name, intrinsic, precision", [
    ("LfricIntegerScalarDataType", "LfricIntegerScalarDataSymbol",
     ScalarType.Intrinsic.INTEGER, lfric_psyir.I_DEF),
    ("LfricRealScalarDataType", "LfricRealScalarDataSymbol",
     ScalarType.Intrinsic.REAL, lfric_psyir.R_DEF),
    ("LfricLogicalScalarDataType", "LfricLogicalScalarDataSymbol",
     ScalarType.Intrinsic.BOOLEAN, lfric_psyir.L_DEF)])
def test_generic_scalars(data_type_name, symbol_name, intrinsic, precision):
    '''Test the generated generic scalar datatypes and symbols are created
    correctly.

    '''
    lfric_types = LFRicTypes()
    data_type = lfric_types(data_type_name)
    symbol = lfric_types(symbol_name)
    # datatype
    lfric_datatype = data_type()
    assert lfric_datatype.intrinsic == intrinsic
    assert lfric_datatype.precision is precision
    # precision can be set explicitly
    lfric_datatype = data_type(precision=4)
    assert lfric_datatype.precision == 4
    # symbol
    lfric_symbol = symbol("symbol")
    assert lfric_symbol.name == "symbol"
    assert isinstance(lfric_symbol.interface, LocalInterface)
    assert isinstance(lfric_symbol.datatype, data_type)
    lfric_symbol = symbol(
        "symbol", interface=ArgumentInterface(ArgumentInterface.Access.READ))
    assert isinstance(lfric_symbol.interface, ArgumentInterface)
    assert lfric_symbol.interface.access == ArgumentInterface.Access.READ
    # precision can be set explicitly
    lfric_symbol = symbol("symbol", precision=4)
    assert lfric_symbol.datatype.precision == 4


# Scalar literals
def test_scalar_literals():
    '''Test the scalar literals are defined correctly.'''
    # LfricDimension class
    lfric_types = LFRicTypes()
    lfric_dim_class = lfric_types("LfricDimension")
    assert isinstance(lfric_types("LfricDimension")("1"),
                      lfric_dim_class)
    assert isinstance(lfric_types("LfricDimension")("3"),
                      lfric_dim_class)
    with pytest.raises(ValueError) as info:
        lfric_types("LfricDimension")("2")
    assert ("An LFRic dimension object must be '1' or '3', but found '2'."
            in str(info.value))
    # LFRIC_SCALAR_DIMENSION instance
    assert isinstance(lfric_types("LFRIC_SCALAR_DIMENSION"), lfric_dim_class)
    assert lfric_types("LFRIC_SCALAR_DIMENSION").value == "1"
    # LFRIC_VECTOR_DIMENSION instance
    assert isinstance(lfric_types("LFRIC_VECTOR_DIMENSION"),
                      lfric_dim_class)
    assert lfric_types("LFRIC_VECTOR_DIMENSION").value == "3"


# Specific scalar datatypes
@pytest.mark.parametrize("data_type_name, generic_type_name", [
    ("CellPositionDataType", "LfricIntegerScalarDataType"),
    ("MeshHeightDataType", "LfricIntegerScalarDataType"),
    ("NumberOfCellsDataType", "LfricIntegerScalarDataType"),
    ("NumberOfDofsDataType", "LfricIntegerScalarDataType"),
    ("NumberOfUniqueDofsDataType", "LfricIntegerScalarDataType"),
    ("NumberOfFacesDataType", "LfricIntegerScalarDataType"),
    ("NumberOfEdgesDataType", "LfricIntegerScalarDataType"),
    ("NumberOfQrPointsInXyDataType", "LfricIntegerScalarDataType"),
    ("NumberOfQrPointsInZDataType", "LfricIntegerScalarDataType"),
    ("NumberOfQrPointsInFacesDataType", "LfricIntegerScalarDataType"),
    ("NumberOfQrPointsInEdgesDataType", "LfricIntegerScalarDataType")])
def test_specific_scalar_types(data_type_name, generic_type_name):
    '''Test the generated specific scalar datatypes are created correctly.

    '''
    lfric_types = LFRicTypes()
    lfric_datatype = lfric_types(data_type_name)()
    assert isinstance(lfric_datatype, lfric_types(generic_type_name))


# Specific scalar symbols
@pytest.mark.parametrize("symbol_name, generic_symbol_name, attribute_map", [
    ("CellPositionDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("MeshHeightDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("NumberOfCellsDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("NumberOfDofsDataSymbol", "LfricIntegerScalarDataSymbol", {"fs": "w3"}),
    ("NumberOfUniqueDofsDataSymbol", "LfricIntegerScalarDataSymbol",
     {"fs": "w2"}),
    ("NumberOfFacesDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("NumberOfEdgesDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("NumberOfQrPointsInXyDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("NumberOfQrPointsInZDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("NumberOfQrPointsInFacesDataSymbol", "LfricIntegerScalarDataSymbol", {}),
    ("NumberOfQrPointsInEdgesDataSymbol", "LfricIntegerScalarDataSymbol", {})])
def test_specific_scalar_symbols(symbol_name, generic_symbol_name,
                                 attribute_map):
    '''Test the generated specific scalar symbols are
    created correctly.

    '''
    lfric_types = LFRicTypes()
    symbol = lfric_types(symbol_name)
    generic_symbol = lfric_types(generic_symbol_name)
    args = ["symbol"] + list(attribute_map.values())
    lfric_symbol = symbol(*args)
    assert isinstance(lfric_symbol, generic_symbol)
    assert lfric_symbol.name == "symbol"
    assert isinstance(lfric_symbol.interface, LocalInterface)
    for attribute in attribute_map:
        assert getattr(lfric_symbol, attribute) == attribute_map[attribute]
    lfric_symbol = symbol(
        *args, interface=ArgumentInterface(ArgumentInterface.Access.READ))
    assert isinstance(lfric_symbol.interface, ArgumentInterface)
    assert lfric_symbol.interface.access == ArgumentInterface.Access.READ


# Specific scalar datatypes
@pytest.mark.parametrize(
    "data_type_name, symbol_name, scalar_type_name, dims_args,"
    "attribute_map",
    [("RealFieldDataDataType", "RealFieldDataDataSymbol",
      "LfricRealScalarDataType",
      [("NumberOfUniqueDofsDataSymbol", "ndofs", "w0")], {"fs": "w0"}),
     ("IntegerFieldDataDataType", "IntegerFieldDataDataSymbol",
      "LfricIntegerScalarDataType",
      [("NumberOfUniqueDofsDataSymbol", "ndofs", "w1")], {"fs": "w1"}),
     ("LogicalFieldDataDataType", "LogicalFieldDataDataSymbol",
      "LfricLogicalScalarDataType",
      [("NumberOfUniqueDofsDataSymbol", "ndofs", "w2")], {"fs": "w2"}),
     ("OperatorDataType", "OperatorDataSymbol",
      "LfricRealScalarDataType",
      [("NumberOfDofsDataSymbol", "ndofs", "w3"),
       ("NumberOfDofsDataSymbol", "ndofs", "w3"),
       ("NumberOfCellsDataSymbol", "ncells")],
     {"fs_from": "w3", "fs_to": "w3"}),
     ("DofMapDataType", "DofMapDataSymbol",
      "LfricIntegerScalarDataType",
      [("NumberOfDofsDataSymbol", "ndofs", "w3")], {"fs": "w3"}),
     ("BasisFunctionQrXyozDataType", "BasisFunctionQrXyozDataSymbol",
      "LfricRealScalarDataType",
      [1,
       ("NumberOfDofsDataSymbol", "ndofs", "w0"),
       ("NumberOfQrPointsInXyDataSymbol", "qr_xy"),
       ("NumberOfQrPointsInZDataSymbol", "qr_z")], {"fs": "w0"}),
     ("BasisFunctionQrFaceDataType", "BasisFunctionQrFaceDataSymbol",
      "LfricRealScalarDataType",
      [3,
       ("NumberOfDofsDataSymbol", "ndofs", "w1"),
       ("NumberOfQrPointsInFacesDataSymbol", "qr"),
       ("NumberOfFacesDataSymbol", "nfaces")], {"fs": "w1"}),
     ("BasisFunctionQrEdgeDataType", "BasisFunctionQrEdgeDataSymbol",
      "LfricRealScalarDataType",
      [1,
       ("NumberOfDofsDataSymbol", "ndofs", "w2"),
       ("NumberOfQrPointsInEdgesDataSymbol", "qr"),
       ("NumberOfEdgesDataSymbol", "nedges")], {"fs": "w2"}),
     ("DiffBasisFunctionQrXyozDataType", "DiffBasisFunctionQrXyozDataSymbol",
      "LfricRealScalarDataType",
      [3,
       ("NumberOfDofsDataSymbol", "ndofs", "wtheta"),
       ("NumberOfQrPointsInXyDataSymbol", "qr_xy"),
       ("NumberOfQrPointsInZDataSymbol", "qr_z")], {"fs": "wtheta"}),
     ("DiffBasisFunctionQrFaceDataType", "DiffBasisFunctionQrFaceDataSymbol",
      "LfricRealScalarDataType",
      [3,
       ("NumberOfDofsDataSymbol", "ndofs", "w1"),
       ("NumberOfQrPointsInFacesDataSymbol", "qr"),
       ("NumberOfFacesDataSymbol", "nfaces")], {"fs": "w1"}),
     ("DiffBasisFunctionQrEdgeDataType", "DiffBasisFunctionQrEdgeDataSymbol",
      "LfricRealScalarDataType",
      [1,
       ("NumberOfDofsDataSymbol", "ndofs", "w2v"),
       ("NumberOfQrPointsInEdgesDataSymbol", "qr"),
       ("NumberOfEdgesDataSymbol", "nedges")], {"fs": "w2v"}),
     ("QrWeightsInXyDataType", "QrWeightsInXyDataSymbol",
      "LfricRealScalarDataType",
      [("NumberOfQrPointsInXyDataSymbol", "qr_xy")], {}),
     ("QrWeightsInZDataType", "QrWeightsInZDataSymbol",
      "LfricRealScalarDataType",
      [("NumberOfQrPointsInZDataSymbol", "qr_z")], {}),
     ("QrWeightsInFacesDataType", "QrWeightsInFacesDataSymbol",
      "LfricRealScalarDataType",
      [("NumberOfQrPointsInFacesDataSymbol", "qr")], {}),
     ("QrWeightsInEdgesDataType", "QrWeightsInEdgesDataSymbol",
      "LfricRealScalarDataType",
      [("NumberOfQrPointsInEdgesDataSymbol", "qr")], {})])
def test_arrays(data_type_name, symbol_name, scalar_type_name,
                dims_args, attribute_map):
    '''Test the generated array datatypes and datasymbols are created
    correctly. This includes field datatypes and symbols which are
    kept as a separate list in psyir.py

    '''
    lfric_types = LFRicTypes()
    dims = []
    # Each dimension arg is either an integer number, or a tuple consisting of
    # an LFRic data type, followed by additional constructor arguments. Use
    # this to create the required list of dimensions:
    for i in dims_args:
        if isinstance(i, int):
            dims.append(i)
        else:
            # Tage the additional constructor arguments
            args = i[1:]
            interface = ArgumentInterface(ArgumentInterface.Access.READ)
            ref = Reference(lfric_types(i[0])(*args,
                                              interface=interface))
            dims.append(ref)

    # Datatype creation
    data_type = lfric_types(data_type_name)
    scalar_type = lfric_types(scalar_type_name)
    lfric_datatype = data_type(dims)
    assert isinstance(lfric_datatype, ArrayType)
    assert isinstance(lfric_datatype._datatype, scalar_type)
    for idx, dim in enumerate(lfric_datatype.shape):
        if isinstance(dim.upper, Literal):
            assert dim.upper.value == str(dims[idx])
        elif isinstance(dim.upper, Reference):
            assert dim.upper is dims[idx]
            assert dim.upper.symbol is dims[idx].symbol
        else:
            assert False, "unexpected type of dimension found"
    # Wrong number of dims
    with pytest.raises(TypeError) as info:
        _ = data_type([])
    assert (f"'{type(lfric_datatype).__name__}' expected the number of "
            f"supplied dimensions to be {len(dims)} but found 0." in
            str(info.value))
    # Datasymbol creation
    args = list(attribute_map.values())
    symbol = lfric_types(symbol_name)
    lfric_symbol = symbol("symbol", dims, *args)
    assert isinstance(lfric_symbol, DataSymbol)
    assert lfric_symbol.name == "symbol"
    assert isinstance(lfric_symbol.interface, LocalInterface)
    assert isinstance(lfric_symbol.datatype, data_type)
    lfric_symbol = symbol(
        "symbol", dims, *args,
        interface=ArgumentInterface(ArgumentInterface.Access.READ))
    assert isinstance(lfric_symbol.interface, ArgumentInterface)
    assert lfric_symbol.interface.access == ArgumentInterface.Access.READ


# Vector field-data data-symbols
@pytest.mark.parametrize(
    "symbol, parent_symbol, space, visibility",
    [("RealVectorFieldDataDataSymbol", "RealFieldDataDataSymbol",
      "w0", None),
     ("IntegerVectorFieldDataDataSymbol", "IntegerFieldDataDataSymbol",
      "w1", Symbol.Visibility.PUBLIC),
     ("LogicalVectorFieldDataDataSymbol", "LogicalFieldDataDataSymbol",
      "w2", Symbol.Visibility.PRIVATE)])
def test_vector_fields(symbol, parent_symbol, space, visibility):
    '''Test the generated vector field datasymbols are created
    correctly. These are straight subclasses of the equivalent field
    datasymbols.

    '''
    lfric_types = LFRicTypes()

    kwargs = {"interface": ArgumentInterface(ArgumentInterface.Access.READ)}
    if visibility is not None:
        kwargs["visibility"] = visibility
    ref = Reference(lfric_types("NumberOfUniqueDofsDataSymbol")(
                    "ndofs", space, **kwargs))
    args = [space]
    lfric_symbol = lfric_types(symbol)("symbol", [ref], *args)
    assert isinstance(lfric_symbol, lfric_types(parent_symbol))
    assert lfric_symbol.name == "symbol"
    assert lfric_symbol.fs == space
    if visibility is None:
        assert ref.symbol.visibility == lfric_symbol.DEFAULT_VISIBILITY
    else:
        assert ref.symbol.visibility == visibility
