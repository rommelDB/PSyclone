# -----------------------------------------------------------------------------
# BSD 3-Clause License
#
# Copyright (c) 2018, Science and Technology Facilities Council
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
# -----------------------------------------------------------------------------

''' This module provides support for adding profiling to code
    generated by PSyclone. '''

from __future__ import absolute_import, print_function
from psyclone.f2pygen import CallGen, TypeDeclGen, UseGen
from psyclone.psyGen import colored, GenerationError, Kern, NameSpace, \
     NameSpaceFactory, Node, SCHEDULE_COLOUR_MAP


class Profiler(object):
    ''' This class wraps all profiling related settings.'''

    # Command line option to use for the various profiling options
    # INVOKES: Automatically add a region for each invoke. i.e. at
    #          the start and end of each PSyclone created subroutine.
    # KERNELS: Automatically add a profile region around every
    #          kernel call including the loop structure created.
    INVOKES = "invokes"
    KERNELS = "kernels"
    SUPPORTED_OPTIONS = [INVOKES, KERNELS]
    _options = []
    # A namespace manager to make sure we get unique region names
    _namespace = NameSpace()

    # -------------------------------------------------------------------------
    @staticmethod
    def set_options(options):
        '''Sets the option the user required.
        :param options: List of options selected by the user, or None to
                        disable all automatic profiling.
        :type options: List of strings.
        :raises GenerationError: If any option is not KERNELS or INVOKES.
        '''
        # Test that all options are valid
        if options is None:
            options = []   # Makes it easier to test
        for index, option in enumerate(options):
            if option not in [Profiler.INVOKES, Profiler.KERNELS]:
                # Create a 'nice' representation of the allowed options.
                # [1:-1] cuts out the '[' and ']' that surrounding the
                # string of the list.
                allowed_options = str(Profiler.SUPPORTED_OPTIONS)[1:-1]
                raise GenerationError("Error in Profiler.setOptions: options "
                                      "must be one of {0} but found '{1}' "
                                      "at {2}"
                                      .format(allowed_options,
                                              str(option), index))

        # Store options so they can be queried later
        Profiler._options = options

    # -------------------------------------------------------------------------
    @staticmethod
    def profile_kernels():
        '''Returns true if kernel profiling is enabled.
        :return: True if kernels should be profiled.
        :rtype: bool'''
        return Profiler.KERNELS in Profiler._options

    # -------------------------------------------------------------------------
    @staticmethod
    def profile_invokes():
        '''Returns true if invoke profiling is enabled.
        :return: True if invokes should be profiled.
        :rtype: bool'''
        return Profiler.INVOKES in Profiler._options

    # -------------------------------------------------------------------------
    @staticmethod
    def add_profile_nodes(schedule, loop_class):
        '''This function inserts all required Profiling Nodes (for invokes
        and kernels, as specified on the command line) into a schedule.
        :param schedule: The schedule to instrument.
        :type schedule: :py::class::`psyclone.psyGen.InvokeSchedule` or \
                        derived class
        :param loop_class: The loop class (e.g. GOLoop, DynLoop) to instrument.
        :type loop_class: :py::class::`psyclone.psyGen.Loop` or derived class.
        '''

        from psyclone.transformations import ProfileRegionTrans
        profile_trans = ProfileRegionTrans()
        if Profiler.profile_kernels():
            for i in schedule.children:
                if isinstance(i, loop_class):
                    profile_trans.apply(i)
        if Profiler.profile_invokes():
            profile_trans.apply(schedule.children)

    # -------------------------------------------------------------------------
    @staticmethod
    def create_unique_region(name):
        '''This function makes sure that region names are unique even if
        the same kernel is called.
        :param str name: The name of a region (usually kernel name).
        :return str: A unique name based on the parameter name.
        '''
        return Profiler._namespace.create_name(name)


# =============================================================================
class ProfileNode(Node):
    '''
    This class can be inserted into a schedule to create profiling code.

    :param children: A list of children nodes for this node.
    :type children: A list of :py::class::`psyclone.psyGen.Node` \
                   or derived classes.
    :param parent: The parent of this node in the PSyIR.
    :type parent: A :py::class::`psyclone.psyGen.Node`.

    '''
    fortran_module = "profile_mod"  #: Profiling interface Fortran module

    def __init__(self, children=None, parent=None):
        Node.__init__(self, children=children, parent=parent)

        # Store the name of the profile variable that is used for this
        # profile name. This allows to show the variable name in __str__
        # (and also if we would call create_name in gen(), the name would
        # change every time gen() is called).
        self._var_name = NameSpaceFactory().create().create_name("profile")

        # Name of the region. In general at constructor time we might not
        # have a parent subroutine or a child for the kernel, so we leave
        # the name empty for now. The region and module names are set the
        # first time gen() is called (and then remain unchanged).
        self._region_name = None
        self._module_name = None

    # -------------------------------------------------------------------------
    def __str__(self):
        ''' Returns a string representation of the subtree starting at
        this node. '''
        result = "ProfileStart[var={0}]\n".format(self._var_name)
        for child in self.children:
            result += str(child)+"\n"
        return result+"ProfileEnd"

    # -------------------------------------------------------------------------
    @property
    def coloured_text(self):
        '''
        Return text containing the (coloured) name of this node type

        :return: the name of this node type, possibly with control codes
                 for colour
        :rtype: string
        '''
        return colored("Profile", SCHEDULE_COLOUR_MAP["Profile"])

    # -------------------------------------------------------------------------
    def view(self, indent=0):
        '''Class specific view function to print the tree.
        Parameters:
        :param int indent: Indentation to be used for this node.'''
        # pylint: disable=arguments-differ
        print(self.indent(indent) + self.coloured_text)
        for entity in self._children:
            entity.view(indent=indent + 1)

    # -------------------------------------------------------------------------
    def gen_code(self, parent):
        # pylint: disable=arguments-differ
        '''Creates the profile start and end calls, surrounding the children
        of this node.

        :param parent: The parent of this node.
        :type parent: :py:class:`psyclone.psyGen.Node`.

        '''
        if self._module_name is None or self._region_name is None:
            # Find the first kernel and use its name. In an untransformed
            # Schedule there should be only one kernel, but if Profile is
            # invoked after e.g. a loop merge more kernels might be there.
            region_name = "unknown-kernel"
            module_name = "unknown-module"
            for kernel in self.walk(self.children, Kern):
                region_name = kernel.name
                module_name = kernel.module_name
                break
            if self._region_name is None:
                self._region_name = Profiler.create_unique_region(region_name)
            if self._module_name is None:
                self._module_name = module_name

        # Note that adding a use statement makes sure it is only
        # added once, so we don't need to test this here!
        use = UseGen(parent, self.fortran_module, only=True,
                     funcnames=["ProfileData, ProfileStart, ProfileEnd"])
        parent.add(use)
        prof_var_decl = TypeDeclGen(parent, datatype="ProfileData",
                                    entity_decls=[self._var_name],
                                    save=True)
        parent.add(prof_var_decl)

        prof_start = CallGen(parent, "ProfileStart",
                             ["\"{0}\"".format(self._module_name),
                              "\"{0}\"".format(self._region_name),
                              self._var_name])
        parent.add(prof_start)

        for child in self.children:
            child.gen_code(parent)

        prof_end = CallGen(parent, "ProfileEnd",
                           [self._var_name])
        parent.add(prof_end)

    # -------------------------------------------------------------------------
    def gen_c_code(self, indent=0):
        '''
        Generates a string representation of this Node using C language
        (currently not supported).

        :param int indent: Depth of indent for the output string.
        :raises NotImplementedError: Not yet supported for profiling.
        '''
        raise NotImplementedError("Generation of C code is not supported "
                                  "for profiling")

    def update(self):
        '''
        Update the underlying fparser2 parse tree to implement the profiling
        region represented by this Node.

        '''
        from fparser.common.sourceinfo import FortranFormat
        from fparser.common.readfortran import FortranStringReader
        from fparser.two.utils import walk_ast
        from fparser.two import Fortran2003
        from psyclone.psyGen import object_index, Schedule
        from psyclone.transformations import TransformationError

        # Ensure child nodes are up-to-date
        super(ProfileNode, self).update()

        # Get the parse tree of the routine containing this region
        ptree = self.root.invoke._ast
        routines = walk_ast([ptree], [Fortran2003.Main_Program,
                                      Fortran2003.Subroutine_Stmt,
                                      Fortran2003.Function_Stmt])
        for routine in routines:
            names = walk_ast([routine], [Fortran2003.Name])
            routine_name = str(names[0]).lower()
            break

        spec_parts = walk_ast([ptree], [Fortran2003.Specification_Part])
        if not spec_parts:
            # TODO add a Specification_Part if necessary
            return
        spec_part = spec_parts[0]

        # Get the existing use statements
        use_stmts = walk_ast(spec_part.content, [Fortran2003.Use_Stmt])
        mod_names = []
        for stmt in use_stmts:
            mod_names.append(str(stmt.items[2]).lower())

        # If we don't already have a use for the profiling module then
        # add one.
        if self.fortran_module not in mod_names:
            reader = FortranStringReader(
                "use profile_mod, only: ProfileData, ProfileStart, ProfileEnd")
            # Tell the reader that the source is free format
            reader.set_format(FortranFormat(True, False))
            use = Fortran2003.Use_Stmt(reader)
            spec_part.content.insert(0, use)

        # Create a name for this region by finding where this profiling
        # node is in the list of profiling nodes in this Invoke.
        sched = self.root
        pnodes = sched.walk(sched.children, ProfileNode)
        region_idx = pnodes.index(self)
        region_name = "r{0}".format(region_idx)
        var_name = "psy_profile{0}".format(region_idx)

        # Create a variable for this profiling region
        reader = FortranStringReader(
            "type(ProfileData), save :: {0}".format(var_name))
        # Tell the reader that the source is free format
        reader.set_format(FortranFormat(True, False))
        decln = Fortran2003.Type_Declaration_Stmt(reader)
        spec_part.content.append(decln)

        # Find the parent in the parse tree
        if isinstance(self.children[0], Schedule):
            # TODO #435 Schedule should really have a valid ast pointer.
            content_ast = self.children[0][0].ast
        else:
            content_ast = self.children[0].ast
        fp_parent = content_ast._parent

        # Find the location of the AST of our first child node in the
        # list of child nodes of our parent in the fparser parse tree.
        ast_start_index = object_index(fp_parent.content,
                                       content_ast)
        # Finding the location of the end is harder as it might be the
        # end of a clause within an If or Select block. We therefore
        # work back up the fparser2 parse tree until we find a node that is
        # a direct child of the parent node.
        ast_end_index = None
        if self.children[-1].ast_end:
            ast_end = self.children[-1].ast_end
        else:
            ast_end = self.children[-1].ast
        while ast_end_index is None:
            try:
                ast_end_index = object_index(fp_parent.content,
                                             ast_end)
            except ValueError:
                # ast_end is not a child of fp_parent so go up to its parent
                # and try again
                ast_end = ast_end._parent
                if hasattr(ast_end, "_parent") and ast_end._parent:
                    ast_end = ast_end._parent
                else:
                    raise TransformationError("TODO")

        # Add the profiling-end call
        reader = FortranStringReader(
            "CALL ProfileEnd({0})".format(var_name))
        # Tell the reader that the source is free format
        reader.set_format(FortranFormat(True, False))
        pecall = Fortran2003.Call_Stmt(reader)
        fp_parent.content.insert(ast_end_index+1, pecall)

        # Add the profiling-start call
        reader = FortranStringReader(
            "CALL ProfileStart('{0}', '{1}', {2})".format(
                routine_name, region_name, var_name))
        reader.set_format(FortranFormat(True, False))
        pscall = Fortran2003.Call_Stmt(reader)
        fp_parent.content.insert(ast_start_index, pscall)
