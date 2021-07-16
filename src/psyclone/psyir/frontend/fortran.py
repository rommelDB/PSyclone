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
# Authors S. Siso, STFC Daresbury Lab
# -----------------------------------------------------------------------------

''' This module provides the PSyIR Fortran front-end.'''

import six
from fparser.common.readfortran import FortranStringReader
from fparser.two import Fortran2003
from fparser.two.parser import ParserFactory
from fparser.two.utils import NoMatchError
from psyclone.psyir.frontend.fparser2 import Fparser2Reader
from psyclone.psyir.nodes import Assignment
from psyclone.psyir.symbols import SymbolError


class FortranReader(object):
    ''' PSyIR Fortran frontend. This frontend translates Fortran from a string
    or a file into PSyIR using the fparser2 utilities.

    '''
    # Save parser object across instances to reduce the initialisation time
    _parser = None

    def __init__(self):
        if not self._parser:
            self._parser = ParserFactory().create(std="f2008")
        self._processor = Fparser2Reader()

    def psyir_from_source(self, source_code):
        ''' Generate the PSyIR tree representing the given Fortran source code.

        :param str source_code: text representation of the code to be parsed.

        :returns: PSyIR representing the provided Fortran source code.
        :rtype: :py:class:`psyclone.psyir.nodes.Node`

        '''
        string_reader = FortranStringReader(source_code)
        parse_tree = self._parser(string_reader)
        psyir = self._processor.generate_psyir(parse_tree)
        return psyir

    def psyir_from_expression(self, source_code):
        '''
        Generate the PSyIR tree for the supplied Fortran expression.
        Currently only supports expressions involving literals - the
        presence of any symbols will result in a NotImplementedError.

        :param str source_code: text of the expression to be parsed.

        :returns: PSyIR representing the provided Fortran expression.
        :rtype: :py:class:`psyclone.psyir.nodes.Node`

        :raises ValueError: if the supplied source does not represent a \
                            Fortran expression.
        :raises NotImplementedError: if the supplied expression contains \
                                     any variable symbols.
        '''
        try:
            parse_tree = Fortran2003.Expr(source_code)
        except NoMatchError as err:
            six.raise_from(
                ValueError("Supplied source does not represent a Fortran "
                           "expression: '{0}'".format(source_code)), err)
        # An Assignment has no symbol table so any attempts to lookup
        # symbols in the supplied expression will raise a Symbol Error
        fake_assign = Assignment()
        try:
            self._processor.process_nodes(fake_assign, [parse_tree])
        except SymbolError as err:
            six.raise_from(
                NotImplementedError("Expression must contain only literals: "
                                    "'{0}'".format(source_code)), err)
        return fake_assign.children[0].detach()

    def psyir_from_file(self, file_path):
        ''' Generate the PSyIR tree representing the given Fortran file.

        :param file_path: path of the file to be read and parsed.
        :type file_path: str or any Python Path format.

        :returns: PSyIR representing the provided Fortran file.
        :rtype: :py:class:`psyclone.psyir.nodes.Node`
        '''
        # Note that this is the main performance hotspot in PSyclone, taking
        # more than 90% of the runtime in some cases. Therefore this is a good
        # place to implement caching in order to avoid repeating parsing steps
        # that have already been done before.

        with open(file_path, "r") as source:
            return self.psyir_from_source(source.read())


# For Sphinx AutoAPI documentation generation
__all__ = ['FortranReader']