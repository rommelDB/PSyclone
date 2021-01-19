# -----------------------------------------------------------------------------
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
# Authors R. W. Ford, A. R. Porter and S. Siso, STFC Daresbury Lab
#         I. Kavcic, Met Office
#         J. Henrichs, Bureau of Meteorology
# -----------------------------------------------------------------------------

''' This module contains the implementation of the abstract ArrayMixin. '''

from __future__ import absolute_import
import abc
import six
from psyclone.psyir.nodes.ranges import Range
from psyclone.psyir.nodes.operation import BinaryOperation
from psyclone.psyir.nodes.literal import Literal
from psyclone.psyir.symbols.datatypes import ScalarType
from psyclone.errors import InternalError


@six.add_metaclass(abc.ABCMeta)
class ArrayMixin(object):
    '''
    Abstract class used to add functionality common to Nodes that represent
    Array accesses.

    '''
    @abc.abstractproperty
    def name(self):
        ''' Returns the name of the node. Abstract here so must be overridden
            in subclass. '''

    @abc.abstractproperty
    def children(self):
        ''' Returns the list of children of this node. Abstract here so must
            be overridden in subclass. '''

    @staticmethod
    @abc.abstractmethod
    def _validate_child(position, child):
        '''
        Checks that the supplied child node is valid at the supplied position.
        Abstract here so must be overridden in subclass.
        '''

    @classmethod
    def _create_array_member(cls, member_name, indices=None,
                             inner_member=None, parent=None):
        '''
        Create an access to (one or more elements of) an array within a
        structure. The array may or may not itself be of structure type. If
        it is then ``inner_member`` specifies the Member of that structure
        that is accessed.

        :param str member_name: the name of the array member of the structure \
            that is being accessed.
        :param indices: the array-index expressions or None.
        :param inner_member: the member of the `member_name` structure that \
            is being accessed.
        :type inner_member: :py:class:`psyclone.psyir.nodes.Member`
        :type indices: list of :py:class:`psyclone.psyir.nodes.DataNode`
        :param parent: the parent of this node in the PSyIR tree.
        :type parent: subclass of :py:class:`psyclone.psyir.nodes.Node`

        :returns: a new instance of type `cls`.
        :rtype: `cls`

        '''
        obj = cls(member_name, parent=parent)
        # Add any child Member as the first child
        if inner_member:
            obj.addchild(inner_member)
            inner_member.parent = obj
        # Add any array-index expressions as children
        if indices:
            for child in indices:
                obj.addchild(child)
                child.parent = obj
        return obj

    def reference_accesses(self, var_accesses):
        '''Get all variable access information. All variables used as indices
        in the access of the array will be added as READ.

        :param var_accesses: variable access information.
        :type var_accesses: \
            :py:class:`psyclone.core.access_info.VariablesAccessInfo`

        '''
        # Now add all children: Note that the class Reference
        # does not recurse to the children (which store the indices), so at
        # this stage no index information has been stored:
        list_indices = []
        for child in self.children:
            child.reference_accesses(var_accesses)
            list_indices.append(child)

        if list_indices:
            var_info = var_accesses[self.name]
            # The last entry in all_accesses is the one added above
            # in super(ArrayReference...). Add the indices to that entry.
            var_info.all_accesses[-1].indices = list_indices

    def _validate_index(self, index):
        '''Utility function that checks that the supplied index is an integer
        and is less than the number of array dimensions.

        :param int index: the array index to check.

        :raises TypeError: if the index argument is not an integer.
        :raises ValueError: if the index value is greater than the \
            number of dimensions in the array (-1).

        '''
        if not isinstance(index, int):
            raise TypeError(
                "The index argument should be an integer but found '{0}'."
                "".format(type(index).__name__))
        if index > len(self.children)-1:
            raise ValueError(
                "In ArrayReference '{0}' the specified index '{1}' must be "
                "less than the number of dimensions '{2}'."
                "".format(self.name, index, len(self.children)))

    def is_lower_bound(self, index):
        '''Returns True if the specified array index contains a Range node
        which has a starting value given by the 'LBOUND(name,index)'
        intrinsic where 'name' is the name of the current Array and
        'index' matches the specified array index. Otherwise False is
        returned.

        For example, if a Fortran array A was declared as
        A(10) then the starting value is 1 and LBOUND(A,1) would
        return that value.

        :param int index: the array index to check.

        :returns: True if the array index is a range with its start \
            value being LBOUND(array,index) and False otherwise.
        :rtype: bool

        '''
        from psyclone.psyir.nodes.reference import Reference
        self._validate_index(index)

        array_dimension = self.children[index]
        if not isinstance(array_dimension, Range):
            return False

        lower = array_dimension.children[0]
        if not (isinstance(lower, BinaryOperation) and
                lower.operator == BinaryOperation.Operator.LBOUND):
            return False
        if not (isinstance(lower.children[0], Reference) and
                lower.children[0].name == self.name):
            return False
        if not (isinstance(lower.children[1], Literal) and
                lower.children[1].datatype.intrinsic ==
                ScalarType.Intrinsic.INTEGER
                and lower.children[1].value == str(index+1)):
            return False
        return True

    def is_upper_bound(self, index):
        '''Returns True if the specified array index contains a Range node
        which has a stopping value given by the 'UBOUND(name,index)'
        intrinsic where 'name' is the name of the current ArrayReference and
        'index' matches the specified array index. Otherwise False is
        returned.

        For example, if a Fortran array A was declared as
        A(10) then the stopping value is 10 and UBOUND(A,1) would
        return that value.

        :param int index: the array index to check.

        :returns: True if the array index is a range with its stop \
            value being UBOUND(array,index) and False otherwise.
        :rtype: bool

        '''
        from psyclone.psyir.nodes.reference import Reference
        self._validate_index(index)

        array_dimension = self.children[index]
        if not isinstance(array_dimension, Range):
            return False

        upper = array_dimension.children[1]
        if not (isinstance(upper, BinaryOperation) and
                upper.operator == BinaryOperation.Operator.UBOUND):
            return False
        if not (isinstance(upper.children[0], Reference) and
                upper.children[0].name == self.name):
            return False
        if not (isinstance(upper.children[1], Literal) and
                upper.children[1].datatype.intrinsic ==
                ScalarType.Intrinsic.INTEGER
                and upper.children[1].value == str(index+1)):
            return False
        return True

    def is_full_range(self, index):
        '''Returns True if the specified array index is a Range Node that
        specifies all elements in this index. In the PSyIR this is
        specified by using LBOUND(name,index) for the lower bound of
        the range, UBOUND(name,index) for the upper bound of the range
        and "1" for the range step.

        :param int index: the array index to check.

        :returns: True if the access to this array index is a range \
            that specifies all index elements. Otherwise returns \
            False.
        :rtype: bool

        '''
        self._validate_index(index)

        array_dimension = self.children[index]
        if isinstance(array_dimension, Range):
            if self.is_lower_bound(index) and self.is_upper_bound(index):
                step = array_dimension.children[2]
                if (isinstance(step, Literal) and
                        step.datatype.intrinsic == ScalarType.Intrinsic.INTEGER
                        and step.value == "1"):
                    return True
        return False

    def indices(self):
        '''
        Supports semantic-navigation by returning the list of nodes
        representing the index expressions for this array reference.

        :returns: the PSyIR nodes representing the array-index expressions.
        :rtype: list of :py:class:`psyclone.psyir.nodes.Node`

        :raises InternalError: if this node has no children.

        '''
        if not self._children:
            raise InternalError(
                "Array malformed or incomplete: must have one or more "
                "children representing array-index expressions but found "
                "none.")
        for idx, child in enumerate(self._children):
            self._validate_child(idx, child)
        return self.children


# For AutoAPI documentation generation
__all__ = ['ArrayMixin']
