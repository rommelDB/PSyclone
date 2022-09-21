# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2022, Science and Technology Facilities Council
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

'''Module containing tests for the OperatorArg class.

'''
import pytest

from fparser.common.readfortran import FortranStringReader
from fparser.two import Fortran2003
from fparser.two.parser import ParserFactory

from psyclone.domain.lfric.kernel.operator_arg import OperatorArg


def test_init_noargs():
    '''Test that an OperatorArg instance can be created successfully when no
    arguments are provided.

    '''
    operator_arg = OperatorArg()
    assert isinstance(operator_arg, OperatorArg)
    assert operator_arg.form == "GH_OPERATOR"
    assert operator_arg._datatype is None
    assert operator_arg._access is None
    assert operator_arg._function_space1 is None
    assert operator_arg._function_space2 is None


def test_init_invalid():
    '''Test that appropriate exceptions are raised if invalid initial
    values are provided when constructing an instance of the
    OperatorArg class.

    '''
    with pytest.raises(ValueError) as info:
        _ = OperatorArg(datatype="invalid")
    assert ("The second metadata entry for an argument should be a "
            "recognised datatype descriptor (one of ['gh_real']), but "
            "found 'invalid'." in str(info.value))

    with pytest.raises(ValueError) as info:
        _ = OperatorArg(access="invalid")
    assert ("The third metadata entry for an argument should be a "
            "recognised datatype descriptor (one of ['gh_read', 'gh_write', "
            "'gh_readwrite']), but found 'invalid'."
            in str(info.value))

    with pytest.raises(ValueError) as info:
        _ = OperatorArg(function_space1="invalid")
    assert ("The fourth metadata entry for an argument should be a "
            "recognised function space (one of ['w3', 'wtheta', 'w2v', "
            "'w2vtrace', 'w2broken', 'w0', 'w1', 'w2', 'w2trace', 'w2h', "
            "'w2htrace', 'any_w2', 'wchi']), but found 'invalid'."
            in str(info.value))

    with pytest.raises(ValueError) as info:
        _ = OperatorArg(function_space2="invalid")
    assert ("The fifth metadata entry for an argument should be a "
            "recognised function space (one of ['w3', 'wtheta', 'w2v', "
            "'w2vtrace', 'w2broken', 'w0', 'w1', 'w2', 'w2trace', 'w2h', "
            "'w2htrace', 'any_w2', 'wchi']), but found 'invalid'."
            in str(info.value))


def test_init_args():
    '''Test that valid initial values provided when constructing an
    instance of OperatorArg are stored as expected.

    '''
    operator_arg = OperatorArg("GH_REAL", "GH_READ", "W0", "W1")
    assert operator_arg.form == "GH_OPERATOR"
    assert operator_arg._datatype == "GH_REAL"
    assert operator_arg._access == "GH_READ"
    assert operator_arg._function_space1 == "W0"
    assert operator_arg._function_space2 == "W1"


def test_create_from_fortran_string():
    '''Test that the create_from_fortran_string static method works as
    expected. Test for exceptions as well as valid input.

    '''
    with pytest.raises(ValueError) as info:
        _ = OperatorArg.create_from_fortran_string("not valid")
    assert ("Expected kernel metadata to be a Fortran Part_Ref, with "
            "the form 'arg_type(...)' but found 'not valid'."
            in str(info.value))

    fortran_string = "arg_type(GH_OPERATOR, GH_REAL, GH_READ, W0, W1)"
    operator_arg = OperatorArg.create_from_fortran_string(fortran_string)
    assert operator_arg.form == "GH_OPERATOR"
    assert operator_arg._datatype == "GH_REAL"
    assert operator_arg._access == "GH_READ"
    assert operator_arg._function_space1 == "W0"
    assert operator_arg._function_space2 == "W1"


def create_part_ref(fortran_string):
    '''Utility method to create an fparser2 Part_Ref instance from a
    Fortran string.

    :param str fortran_string: the Fortran string to convert.

    :returns: the fparser2 Part_Ref representation of the Fortran string.
    :rtype: :py:class:`fparser.two.Fortran2003.Part_Ref`

    '''
    _ = ParserFactory().create(std="f2003")
    reader = FortranStringReader(fortran_string)
    return Fortran2003.Part_Ref(reader)


def test_create_from_fparser2():
    '''Test that the create_from_fparser2 static method works as
    expected. Test for exceptions as well as valid input.

    '''
    with pytest.raises(TypeError) as info:
        _ = OperatorArg.create_from_fparser2("hello")
    assert ("Expected kernel metadata to be encoded as a Fortran "
            "Part_Ref object but found type 'str' with value 'hello'."
            in str(info.value))

    part_ref = create_part_ref("hello(x)")
    with pytest.raises(ValueError) as info:
        _ = OperatorArg.create_from_fparser2(part_ref)
    assert ("Expected kernel metadata to have the name 'arg_type' "
            "and be in the form 'arg_type(...)', but found 'hello(x)'."
            in str(info.value))

    part_ref = create_part_ref("arg_type(x)")
    with pytest.raises(ValueError) as info:
        _ = OperatorArg.create_from_fparser2(part_ref)
    assert ("Expected kernel metadata to have 5 arguments, but "
            "found 1 in 'arg_type(x)'." in str(info.value))

    part_ref = create_part_ref(
        "arg_type(GH_OPERATOR, GH_REAL, GH_READ, W0, W1)")
    operator_arg = OperatorArg.create_from_fparser2(part_ref)
    assert operator_arg.form == "GH_OPERATOR"
    assert operator_arg._datatype == "GH_REAL"
    assert operator_arg._access == "GH_READ"
    assert operator_arg._function_space1 == "W0"
    assert operator_arg._function_space2 == "W1"


def test_fortran_string():
    '''Test that the fortran_string method works as expected, including
    raising an exception if all of the required properties have not been
    set. '''
    fortran_string = "arg_type(GH_OPERATOR, GH_REAL, GH_READ, W0, W1)"
    operator_arg = OperatorArg.create_from_fortran_string(fortran_string)
    result = operator_arg.fortran_string()
    assert result == fortran_string

    operator_arg = OperatorArg()
    with pytest.raises(ValueError) as info:
        _ = operator_arg.fortran_string()
    assert ("Values for datatype, access, function_space1 and function_space2 "
            "must be provided before calling the fortran_string method, but "
            "found 'None', 'None', 'None' and 'None', respectively."
            in str(info.value))


def test_setter_getter():
    '''Test that the setters and getters work as expected, including
    raising exceptions if values are invalid. '''
    operator_arg = OperatorArg()
    assert operator_arg.form == "GH_OPERATOR"

    assert operator_arg.datatype is None
    with pytest.raises(ValueError) as info:
        operator_arg.datatype = "invalid"
    assert ("The second metadata entry for an argument should be a "
            "recognised datatype descriptor (one of ['gh_real']), but "
            "found 'invalid'." in str(info.value))

    operator_arg.datatype = "gh_real"
    assert operator_arg.datatype == "gh_real"
    operator_arg.datatype = "GH_REAL"
    assert operator_arg.datatype == "GH_REAL"

    assert operator_arg.access is None
    with pytest.raises(ValueError) as info:
        operator_arg.access = "invalid"
    assert ("The third metadata entry for an argument should be a "
            "recognised datatype descriptor (one of ['gh_read', 'gh_write', "
            "'gh_readwrite']), but found 'invalid'."
            in str(info.value))

    operator_arg.access = "gh_read"
    assert operator_arg.access == "gh_read"
    operator_arg.access = "GH_READ"
    assert operator_arg.access == "GH_READ"

    assert operator_arg.function_space1 is None
    with pytest.raises(ValueError) as info:
        operator_arg.function_space1 = "invalid"
    assert ("The fourth metadata entry for an argument should be a "
            "recognised function space (one of ['w3', 'wtheta', 'w2v', "
            "'w2vtrace', 'w2broken', 'w0', 'w1', 'w2', 'w2trace', 'w2h', "
            "'w2htrace', 'any_w2', 'wchi']), but found 'invalid'."
            in str(info.value))

    operator_arg.function_space1 = "w0"
    assert operator_arg.function_space1 == "w0"
    operator_arg.function_space1 = "W0"
    assert operator_arg.function_space1 == "W0"

    assert operator_arg.function_space2 is None
    with pytest.raises(ValueError) as info:
        operator_arg.function_space2 = "invalid"
    assert ("The fifth metadata entry for an argument should be a "
            "recognised function space (one of ['w3', 'wtheta', 'w2v', "
            "'w2vtrace', 'w2broken', 'w0', 'w1', 'w2', 'w2trace', 'w2h', "
            "'w2htrace', 'any_w2', 'wchi']), but found 'invalid'."
            in str(info.value))

    operator_arg.function_space2 = "w1"
    assert operator_arg.function_space2 == "w1"
    operator_arg.function_space2 = "W1"
    assert operator_arg.function_space2 == "W1"
