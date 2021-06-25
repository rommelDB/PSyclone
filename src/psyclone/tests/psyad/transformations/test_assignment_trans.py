# BSD 3-Clause License
#
# Copyright (c) 2021, Science and Technology Facilities Council.
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
# Authors: R. W. Ford and A. R. Porter, STFC Daresbury Lab
#
'''Module to test the psyad assignment transformation.'''

import pytest

from psyclone.psyir.symbols import DataSymbol, REAL_TYPE, SymbolTable
from psyclone.psyir.nodes import BinaryOperation, Reference, Assignment, \
    Routine
from psyclone.psyir.frontend.fortran import FortranReader
from psyclone.psyir.backend.fortran import FortranWriter
from psyclone.psyir.transformations import TransformationError

from psyclone.psyad.transformations import AssignmentTrans, TangentLinearError


def check_adjoint(tl_fortran, active_variable_names, expected_ad_fortran):
    '''Utility routine that takes tangent linear fortran code as input in
    the argument tl_fortran, transforms this code into its adjoint
    using the active variables specified in the active variable_names
    argument and tests whether the result is the same as the expected
    result in the expected_ad_fortran argument.

    :param str tl_fortran: tangent linear code.
    :param list of str active_variable_names: a list of active \
        variable names.
    :param str tl_fortran: the expected adjoint code to be produced.

    '''
    input_code = ("subroutine test()\n{0}end subroutine test\n"
                  "".format(tl_fortran))
    expected_output_code = ("subroutine test()\n{0}end subroutine test\n"
                            "".format(expected_ad_fortran))
    print (input_code)
    reader = FortranReader()
    psyir = reader.psyir_from_source(input_code)
    assignment = psyir.children[0][0]
    assert isinstance(assignment, Assignment)

    symbol_table = assignment.scope.symbol_table
    active_variables = []
    for variable_name in active_variable_names:
        active_variables.append(symbol_table.lookup(variable_name))
    
    trans = AssignmentTrans(active_variables)
    trans.apply(assignment)

    writer = FortranWriter()
    ad_fortran = writer(psyir)

    print (expected_output_code)
    print (ad_fortran)
    assert ad_fortran == expected_output_code


def test_zero():
    '''Test that the adjoint transformation with an assignment of the form
    A = 0. This tests that the transformation works when there are no
    active variables on the rhs and with the active variable on the lhs
    being a write, not an increment. Scalars, directly addressed
    arrays, indirectly addressed arrays and structure array accesses
    are tested.

    A=0 -> A*=0

    '''
    # Scalar
    tl_fortran = (
        "  real :: a\n"
        "  a = 0.0\n")
    active_variables = ["a"]
    ad_fortran = (
        "  real :: a\n\n"
        "  a = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)
    # Direct Addressed Array
    tl_fortran = (
        "  real :: a(n)\n"
        "  integer :: n\n"
        "  a(n) = 0.0\n\n")
    active_variables = ["a"]
    ad_fortran = (
        "  integer :: n\n"
        "  real, dimension(n) :: a\n\n"
        "  a(n) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)
    # Indirect Addressed Array
    tl_fortran = (
        "  real :: a(n)\n"
        "  integer :: b(n), n\n"
        "  a(b(n)) = 0.0\n\n")
    active_variables = ["a"]
    ad_fortran = (
        "  integer :: n\n"
        "  real, dimension(n) :: a\n"
        "  integer, dimension(n) :: b\n\n"
        "  a(b(n)) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)
    # Structure
    tl_fortran = (
        "  use field_mod, only : field_type\n"
        "  type(field_type) :: a\n"
        "  integer :: n\n"
        "  a%data(n) = 0.0\n\n")
    active_variables = ["a"]
    ad_fortran = (
        "  use field_mod, only : field_type\n"
        "  type(field_type) :: a\n"
        "  integer :: n\n\n"
        "  a%data(n) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_single_assign():
    '''Test that the adjoint transformation with an assignment of the form
    A = B. This tests that the transformation works when there is one
    active variable on the rhs and with the active variable on the lhs
    being a write, not an increment. Scalars, directly addressed
    arrays, indirectly addressed arrays and structure array accesses
    are tested.

    A=B -> B*=B*+A*;A*=0.0

    '''
    # Scalar
    tl_fortran = (
        "  real :: a,b\n"
        "  a = b\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  real :: a\n  real :: b\n\n"
        "  b = b + a\n"
        "  a = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)
    # Direct addressed array
    tl_fortran = (
        "  real :: a(n),b(n)\n"
        "  integer :: i,n\n"
        "  a(2*i) = b(n+1)\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  integer :: n\n  real, dimension(n) :: a\n"
        "  real, dimension(n) :: b\n  integer :: i\n\n"
        "  b(n + 1) = b(n + 1) + a(2 * i)\n"
        "  a(2 * i) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)
    # Indirect addressed array
    tl_fortran = (
        "  real :: a(n),b(n)\n"
        "  integer :: i,n,lookup(n)\n"
        "  a(lookup(2*i)) = b(lookup(n)+1)\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  integer :: n\n  real, dimension(n) :: a\n"
        "  real, dimension(n) :: b\n  integer :: i\n"
        "  integer, dimension(n) :: lookup\n\n"
        "  b(lookup(n) + 1) = b(lookup(n) + 1) + a(lookup(2 * i))\n"
        "  a(lookup(2 * i)) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)
    # Structure
    tl_fortran = (
        "  use field_mod, only : field_type\n"
        "  type(field_type) :: a,b\n"
        "  integer :: i,n\n"
        "  a%data(2*i) = b%data(n+1)\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  use field_mod, only : field_type\n"
        "  type(field_type) :: a\n  type(field_type) :: b\n"
        "  integer :: i\n  integer :: n\n\n"
        "  b%data(n + 1) = b%data(n + 1) + a%data(2 * i)\n"
        "  a%data(2 * i) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_single_valued_assign():
    '''Test that the adjoint transformation with an assignment of the form
    A = xB. This tests that the transformation works when there is one
    active variable on the rhs that is multipled by a factor and with
    the active variable on the lhs being a write, not an
    increment.

    A=xB -> B*=B*+xA*;A*=0.0

    '''
    tl_fortran = (
        "  real a(10), b(10), n\n"
        "  integer :: i,j\n"
        "  a(i) = 3*n*b(j)\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  real, dimension(10) :: a\n  real, dimension(10) :: b\n"
        "  real :: n\n  integer :: i\n  integer :: j\n\n"
        "  b(j) = b(j) + a(i) * (3 * n)\n"
        "  a(i) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_multi_add():
    '''Test that the adjoint transformation with an assignment of the form
    A = xB + yC + D. This tests that the transformation works when
    there are many active variables on the rhs with some of them being
    multipled by a factor and with the active variable on the lhs
    being a write, not an increment.

    A=xB+yC+D -> D*=D*+A; C*=C*+yA*; B*=B*+xA*; A*=0.0

    '''
    tl_fortran = (
        "  real a(10), b(10), c(10), d(10)\n"
        "  integer :: i, j, n\n"
        "  a(i+2) = (3/n)*b(j) + c(1)/(2*n) + d(n)\n")
    active_variables = ["a", "b", "c", "d"]
    ad_fortran = (
        "  real, dimension(10) :: a\n  real, dimension(10) :: b\n"
        "  real, dimension(10) :: c\n  real, dimension(10) :: d\n"
        "  integer :: i\n  integer :: j\n  integer :: n\n\n"
        "  b(j) = b(j) + a(i + 2) * (3 / n)\n"
        "  c(1) = c(1) + a(i + 2) / (2 * n)\n"
        "  d(n) = d(n) + a(i + 2)\n"
        "  a(i + 2) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_increment():
    '''Test that the adjoint transformation with an assignment of the form
    A = A. This tests that the transformation works when there are no
    additions on the rhs with the lhs being an increment.

    A=A -> A*=A*

    As A does not change we output nothing.

    '''
    tl_fortran = (
        "  integer :: n\n"
        "  real a(n)\n"
        "  a(n) = a(n)\n")
    active_variables = ["a"]
    ad_fortran = (
        "  integer :: n\n"
        "  real, dimension(n) :: a\n\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_increment_mult():
    '''Test that the adjoint transformation with an assignment of the form
    A = xA. This tests that the transformation works when there are no
    additions on the rhs with the lhs being a scaled increment.

    A=xA -> A*=xA*

    '''
    tl_fortran = (
        "  integer :: n\n"
        "  real a(n)\n"
        "  a(n) = 5*a(n)\n")
    active_variables = ["a"]
    ad_fortran = (
        "  integer :: n\n"
        "  real, dimension(n) :: a\n\n"
        "  a(n) = a(n) * 5\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_increment_add():
    '''Test that the adjoint transformation with an assignment of the form
    A = A + B. This tests that the transformation works when there is
    a single addition on the rhs with the lhs being an increment.

    A+=B -> B*+=A*; A*=A*

    '''
    tl_fortran = (
        "  real a(10), b(10)\n"
        "  a(1) = a(1)+b(1)\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  real, dimension(10) :: a\n"
        "  real, dimension(10) :: b\n\n"
        "  b(1) = b(1) + a(1)\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_increment_add_reorder():
    '''Test that the adjoint transformation with an assignment of the form
    A = B + kA. This tests that the transformation works when there is
    a single addition on the rhs with the lhs being a scaled increment
    and the increment not being on the lhs of the rhs.

    A=B+kA -> B*+=A*; A*=kA*

    '''
    tl_fortran = (
        "  real a(10), b(10)\n"
        "  integer k\n"
        "  a(1) = b(1)+k*a(1)\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  real, dimension(10) :: a\n"
        "  real, dimension(10) :: b\n"
        "  integer :: k\n\n"
        "  b(1) = b(1) + a(1)\n"
        "  a(1) = a(1) * k\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_increment_multi_add():
    '''Test that the adjoint transformation with an assignment of the form
    A = wA + xB + yC + zD. This tests that the transformation works
    when there are multiple additions on the rhs with the lhs being a
    scaled increment.

    A=wA+xB+yC+zD -> D*=D*+zA*; C*=C*+yA*; B*=B*+xA*; A*=wA*

    '''
    tl_fortran = (
        "  real a(10), b(10), c(10), d(10)\n"
        "  real w(10), x, y(10), z\n"
        "  a(1) = w(1)*a(1)+x*b(1)+y(1)*c(1)+z*d(1)\n")
    active_variables = ["a", "b", "c", "d"]
    ad_fortran = (
        "  real, dimension(10) :: a\n  real, dimension(10) :: b\n"
        "  real, dimension(10) :: c\n  real, dimension(10) :: d\n"
        "  real, dimension(10) :: w\n  real :: x\n"
        "  real, dimension(10) :: y\n  real :: z\n\n"
        "  b(1) = b(1) + a(1) * x\n"
        "  c(1) = c(1) + a(1) * y(1)\n"
        "  d(1) = d(1) + a(1) * z\n"
        "  a(1) = a(1) * w(1)\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_multi_increment():
    '''Test that the adjoint transformation with an assignment containing
    multiple increments 
    A = A + xA.

    '''
    tl_fortran = (
        "  real a(10)\n"
        "  real x\n"
        "  a(1) = a(1)+x*a(1)\n")
    active_variables = ["a"]
    ad_fortran = (
        "  real, dimension(10) :: a\n"
        "  real :: x\n\n"
        "  a(1) = a(1) * (1.0 + x)\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_single_valued_sub():
    '''Test that the adjoint transformation with an assignment of the form
    A = -B. This tests that the transformation works when there is one
    active variable on the rhs that is negated with
    the active variable on the lhs being a write, not an
    increment.

    A=-B -> B*=B*-A*;A*=0.0

    '''
    tl_fortran = (
        "  real a(10), b(10)\n"
        "  integer :: i,j\n"
        "  a(i) = -b(j)\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  real, dimension(10) :: a\n  real, dimension(10) :: b\n"
        "  integer :: i\n  integer :: j\n\n"
        "  b(j) = b(j) + a(i) * -1.0\n"
        "  a(i) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_multi_valued_sub():
    '''Test that the adjoint transformation with an assignment of the form
    A = -B -x(+C) + (-D)y. This tests that the transformation works
    when there are multiple active variable on the rhs that have unary
    plus and minus operators as well as minus separating the
    terms. The active variable on the lhs is a write, not an
    increment.

    A=-B-x(+C)+(-D)y -> B*=B*-A*;C*=C*-xA*; D*=D*-yA*; A*=0.0

    '''
    tl_fortran = (
        "  real a(10), b(10), c(10), d(10)\n"
        "  real :: x, y\n"
        "  integer :: i,j\n"
        "  a(i) = -b(j)-x*(+c(i))+(-d(j))*y\n")
    active_variables = ["a", "b", "c", "d"]
    ad_fortran = (
        "  real, dimension(10) :: a\n  real, dimension(10) :: b\n"
        "  real, dimension(10) :: c\n  real, dimension(10) :: d\n"
        "  real :: x\n  real :: y\n  integer :: i\n  integer :: j\n\n"
        "  b(j) = b(j) + a(i) * -1.0\n"
        "  c(i) = c(i) - a(i) * x\n"
        "  d(j) = d(j) + a(i) * (-1.0 * y)\n"
        "  a(i) = 0.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


def test_inc_sub():
    '''Test that the adjoint transformation with an assignment of the form
    A = -A. This tests that the transformation works
    when there is a single increment with a minus operator.

    A=-A -> A*=-A*

    '''
    tl_fortran = (
        "  real a(10)\n"
        "  integer :: i\n"
        "  a(i) = -a(i)\n")
    active_variables = ["a"]
    ad_fortran = (
        "  real, dimension(10) :: a\n"
        "  integer :: i\n\n"
        "  a(i) = a(i) * -1.0\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


# a = -a -x*a + b - a/y
def test_multi_inc_sub():
    '''Test that the adjoint transformation with an assignment of the form
    A = -A -xA + B + A/y. This tests that the transformation works
    when there is are multiple increments with and without a minus
    operator interspersed with another active variable.

    A=-A-xA+B+A/y -> B*=B*+A*; A*=A*(-1.0-x+1.0/y)

    '''
    tl_fortran = (
        "  real a(10), b(10)\n"
        "  integer :: i\n"
        "  real :: x,y\n"
        "  a(i) = -a(i)-x*a(i)+b(i)+a(i)/y\n")
    active_variables = ["a", "b"]
    ad_fortran = (
        "  real, dimension(10) :: a\n  real, dimension(10) :: b\n"
        "  integer :: i\n"
        "  real :: x\n  real :: y\n\n"
        "  b(i) = b(i) + a(i)\n"
        "  a(i) = a(i) * (-1.0 + x + 1.0 / y)\n\n")
    check_adjoint(tl_fortran, active_variables, ad_fortran)


# a(i) = a(i+1) + b(i) + b(i+1)
#
# Mixed case for variables and definitions of active vars.

# * other datatypes (assuming all real for the moment) and ignoring precision

# TODO TEST WHEN active var on LHS of A/x is OK???? Test correct use of divide when multiple terms

# Validate method

#
# Check Error if rhs term does not have any active variables in it as it does not seem to be working.
#

def test_validate_node():
    '''Check that the expected exception is raised if the provided node
    argument is not a PSyIR Assignment node.'''
    trans = AssignmentTrans(active_variables=[])
    with pytest.raises(TransformationError) as info:
        trans.validate(None)
    assert ("Node argument in assignment transformation should be a PSyIR "
            "Assignment, but found 'NoneType'." in str(info.value))


def test_validate_not_active():
    '''Test that the validate method returns without error if there are no
    active variables in the assignment.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol = DataSymbol("b", REAL_TYPE)
    assignment = Assignment.create(Reference(lhs_symbol), Reference(rhs_symbol))
    trans = AssignmentTrans(active_variables=["c", "aa", "ab"])
    trans.validate(assignment)


def test_validate_active_rhs():
    '''Test that the validate method returns the expected exception if
    there is at least one active variable on the RHS of an assignment
    but the LHS is not an active variable.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol = DataSymbol("b", REAL_TYPE)
    assignment = Assignment.create(Reference(lhs_symbol), Reference(rhs_symbol))
    trans = AssignmentTrans(active_variables=["c", "aa", "b"])
    with pytest.raises(TangentLinearError) as info:
        trans.validate(assignment)
    assert ("Assignment node 'a = b\n' has the following active variables on "
            "its RHS '['b']' but its LHS 'a' is not an active variable."
            in str(info.value))

@pytest.mark.parametrize("operator, string",
                         [(BinaryOperation.Operator.ADD, "+"),
                          (BinaryOperation.Operator.SUB, "-")])
def test_validate_rhs_term_active(operator, string):
    '''Test that the validate method returns the expected exception if one
    of the terms on the rhs does not contain an active variable. Split
    rhs terms with + and - to show both work.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol1 = DataSymbol("b", REAL_TYPE)
    rhs_symbol2 = DataSymbol("c", REAL_TYPE)
    addition = BinaryOperation.create(
        operator, Reference(rhs_symbol1), Reference(rhs_symbol2))
    assignment = Assignment.create(Reference(lhs_symbol), addition)
    trans = AssignmentTrans(active_variables=["a", "b"])
    with pytest.raises(TangentLinearError) as info:
        trans.validate(assignment)
    assert ("Each term on the RHS of the assigment 'a = b {0} c\n' must have "
            "an active variable but 'c' does not.".format(string)
            in str(info.value))


def test_validate_rhs_term_multi_active():
    '''Test that the validate method returns the expected exception if one
    of the terms on the rhs contains more than one active variable.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol1 = DataSymbol("b", REAL_TYPE)
    rhs_symbol2 = DataSymbol("c", REAL_TYPE)
    multiply = BinaryOperation.create(
        BinaryOperation.Operator.MUL, Reference(
            rhs_symbol1), Reference(rhs_symbol2))
    assignment = Assignment.create(Reference(lhs_symbol), multiply)
    trans = AssignmentTrans(active_variables=["a", "b", "c"])
    with pytest.raises(TangentLinearError) as info:
        trans.validate(assignment)
    assert ("Each term on the RHS of the assigment 'a = b * c\n' must not "
            "have more than one active variable but 'b * c' has 2."
            in str(info.value))


def test_validate_rhs_single_active_var():
    '''Test that the validate method returns successfully if the
    terms on the RHS of an assignment are single active variables.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol = DataSymbol("b", REAL_TYPE)
    assignment = Assignment.create(Reference(lhs_symbol), Reference(rhs_symbol))
    trans = AssignmentTrans(active_variables=["a", "b"])
    trans.validate(assignment)


@pytest.mark.parametrize("operator", [BinaryOperation.Operator.MUL,
                                      BinaryOperation.Operator.DIV])
def test_validate_rhs_active_var_mul(operator):
    '''Test that the validate method returns successfully if the term on
    the RHS of an assignment contains an active variable that is part
    of a set of multiplications or divides.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol1 = DataSymbol("b", REAL_TYPE)
    rhs_symbol2 = DataSymbol("x", REAL_TYPE)
    rhs_symbol3 = DataSymbol("y", REAL_TYPE)
    multiply1 = BinaryOperation.create(
        BinaryOperation.Operator.MUL, Reference(
            rhs_symbol2), Reference(rhs_symbol1))
    multiply2 = BinaryOperation.create(
        operator, Reference(rhs_symbol3), multiply1)
    assignment = Assignment.create(Reference(lhs_symbol), multiply2)
    trans = AssignmentTrans(active_variables=["a", "b"])
    trans.validate(assignment)


def test_validate_rhs_active_var_no_mul():
    '''Test that the validate method fails if the term on the RHS of the
    assignment contains an active variable that is not part of a set
    of multiplications or divides.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol1 = DataSymbol("b", REAL_TYPE)
    rhs_symbol2 = DataSymbol("x", REAL_TYPE)
    power = BinaryOperation.create(
        BinaryOperation.Operator.POW, Reference(
            rhs_symbol1), Reference(rhs_symbol2))
    assignment = Assignment.create(Reference(lhs_symbol), power)
    trans = AssignmentTrans(active_variables=["a", "b"])
    with pytest.raises(TangentLinearError) as info:
        trans.validate(assignment)
    assert ("Each term on the RHS of the assignment 'a = b ** x\n' must be "
            "an active variable multiplied or divided by an expression, but "
            "found 'b ** x'." in str(info.value))


# TODO: Test this raises an exception too A = y*(B+z) + C
# TODO TEST WHEN index=0. Need special case?????
# TODO TEST WHEN active var on LHS of A/x is OK????

def test_validate_rhs_active_divisor():
    '''Test that the validate method raises the expected exception if a
    term on the RHS of an assignment has an active variable as a
    divisor.'''
    lhs_symbol = DataSymbol("a", REAL_TYPE)
    rhs_symbol1 = DataSymbol("b", REAL_TYPE)
    rhs_symbol2 = DataSymbol("x", REAL_TYPE)
    divide = BinaryOperation.create(
        BinaryOperation.Operator.DIV, Reference(
            rhs_symbol2), Reference(rhs_symbol1))
    assignment = Assignment.create(Reference(lhs_symbol), divide)
    trans = AssignmentTrans(active_variables=["a", "b"])
    with pytest.raises(TangentLinearError) as info:
        trans.validate(assignment)
    assert ("A term on the RHS of the assignment 'a = x / b\n' with a "
            "division must not have the active variable as a divisor but "
            "found 'x / b'." in str(info.value))

# TODO FAIL if A*func(a)

# TODO Check validate tests work independent of case of variable (as use lower())

# Restructure apply (and make multi-increment work?)
# Multi-increment raise error a = a + a + b as the current logic does not work in this case.???

# TODO test _split_nodes
# TODO test _process (after restructuring)
# TODO check apply tests (after restructuring)
