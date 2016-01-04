# ----------------------------------------------------------------------------
# (c) The copyright relating to this work is owned jointly by the Crown,
# Met Office and NERC 2014.
# However, it has been created with the help of the GungHo Consortium,
# whose members are identified at https://puma.nerc.ac.uk/trac/GungHo/wiki
# ----------------------------------------------------------------------------
# Author R. Ford STFC Daresbury Lab

from f2pygen import ModuleGen, CommentGen, SubroutineGen, DoGen, CallGen,\
    AllocateGen, DeallocateGen, IfThenGen, DeclGen, TypeDeclGen,\
    ImplicitNoneGen, UseGen, DirectiveGen
from utils import line_number, count_lines
import pytest


class TestDeclare:
    ''' pytest test for a declaration '''
    def test_no_replication_scalars(self):
        '''Check that the same scalar variable will only get declared once in
           a module and a subroutine'''
        variable_name = "arg_name"
        datatype = "integer"
        module = ModuleGen(name="testmodule")
        module.add(DeclGen(module, datatype=datatype,
                           entity_decls=[variable_name]))
        module.add(DeclGen(module, datatype=datatype,
                           entity_decls=[variable_name]))
        subroutine = SubroutineGen(module, name="testsubroutine")
        module.add(subroutine)
        subroutine.add(DeclGen(subroutine, datatype=datatype,
                               entity_decls=[variable_name]))
        subroutine.add(DeclGen(subroutine, datatype=datatype,
                               entity_decls=[variable_name]))
        generated_code = str(module.root)
        assert generated_code.count(variable_name) == 2

    def test_no_replication_types(self):
        '''Check that the same array variable will only get declared once in
           a module and a subroutine'''
        variable_name = "arg_name"
        datatype = "field_type"
        module = ModuleGen(name="testmodule")
        module.add(TypeDeclGen(module, datatype=datatype,
                               entity_decls=[variable_name]))
        module.add(TypeDeclGen(module, datatype=datatype,
                               entity_decls=[variable_name]))
        subroutine = SubroutineGen(module, name="testsubroutine")
        module.add(subroutine)
        subroutine.add(TypeDeclGen(subroutine, datatype=datatype,
                                   entity_decls=[variable_name]))
        subroutine.add(TypeDeclGen(subroutine, datatype=datatype,
                                   entity_decls=[variable_name]))
        generated_code = str(module.root)
        assert generated_code.count(variable_name) == 2

    def test_subroutine_var_with_implicit_none(self):
        ''' test that a variable is added after an implicit none
        statement in a subroutine'''
        module = ModuleGen(name="testmodule")
        subroutine = SubroutineGen(module, name="testsubroutine",
                                   implicitnone=True)
        module.add(subroutine)
        subroutine.add(DeclGen(subroutine, datatype="integer",
                               entity_decls=["var1"]))
        idx_var = line_number(subroutine.root, "INTEGER var1")
        idx_imp_none = line_number(subroutine.root, "IMPLICIT NONE")
        print str(module.root)
        assert idx_var - idx_imp_none == 1, \
            "variable declation must be after implicit none"

    def test_subroutine_var_intent_in_with_directive(self):
        ''' test that a variable declared as intent in is added before
        a directive in a subroutine'''
        module = ModuleGen(name="testmodule")
        subroutine = SubroutineGen(module, name="testsubroutine",
                                   implicitnone=False)
        module.add(subroutine)
        subroutine.add(DirectiveGen(subroutine, "omp", "begin",
                                    "parallel", ""))
        subroutine.add(DeclGen(subroutine, datatype="integer",
                               intent="in", entity_decls=["var1"]))
        idx_par = line_number(subroutine.root, "!$omp parallel")
        idx_var = line_number(subroutine.root,
                              "INTEGER, intent(in) :: var1")
        print str(module.root)
        assert idx_par - idx_var == 1, \
            "variable declaration must be before directive"


class TestIf:
    ''' pytest test for if statements. '''

    def test_if(self):
        ''' Check that an if gets created succesfully. '''
        module = ModuleGen(name="testmodule")
        clause = "a < b"
        fortran_if = IfThenGen(module, clause)
        module.add(fortran_if)
        lines = str(module.root).splitlines()
        assert "IF (" + clause + ") THEN" in lines[3]
        assert "END IF" in lines[4]

    def test_if(self):
        ''' Check that the content of an if gets created successfully. '''
        module = ModuleGen(name="testmodule")
        clause = "a < b"
        if_statement = IfThenGen(module, clause)
        if_statement.add(CommentGen(if_statement, "HELLO"))
        module.add(if_statement)
        lines = str(module.root).splitlines()
        assert "IF (" + clause + ") THEN" in lines[3]
        assert "!HELLO" in lines[4]
        assert "END IF" in lines[5]


class TestComment:
    ''' pytest tests for comments. '''
    def test_comment(self):
        ''' check that a comment gets created succesfully. '''
        module = ModuleGen(name="testmodule")
        content = "HELLO"
        comment = CommentGen(module, content)
        module.add(comment)
        lines = str(module.root).splitlines()
        assert "!" + content in lines[3]


class TestAdd:
    ''' pytest tests for adding code. '''
    def test_add_before(self):
        ''' add the new code before a particular object '''
        module = ModuleGen(name="testmodule")
        subroutine = SubroutineGen(module, name="testsubroutine")
        module.add(subroutine)
        loop = DoGen(subroutine, "it", "1", "10")
        subroutine.add(loop)
        call = CallGen(subroutine, "testcall")
        subroutine.add(call, position=["before", loop.root])
        lines = str(module.root).splitlines()
        # the call should be inserted before the loop
        print lines
        assert "SUBROUTINE testsubroutine" in lines[3]
        assert "CALL testcall" in lines[4]
        assert "DO it=1,10" in lines[5]


class TestModuleGen:
    ''' pytest tests for the ModuleGen class '''
    def test_vanilla(self):
        module = ModuleGen()
        lines = str(module.root).splitlines()
        assert "MODULE" in lines[0]
        assert "IMPLICIT NONE" in lines[1]
        assert "CONTAINS" in lines[2]
        assert "END MODULE" in lines[3]

    def test_module_name(self):
        name = "test"
        module = ModuleGen(name=name)
        assert "MODULE " + name in str(module.root)

    def test_no_contains(self):
        module = ModuleGen(name="test", contains=False)
        assert "CONTAINS" not in str(module.root)

    def test_no_implicit_none(self):
        module = ModuleGen(name="test", implicitnone=False)
        assert "IMPLICIT NONE" not in str(module.root)

    def test_failed_module_inline(self):
        ''' test that an error is thrown if the wrong type of object
        is passed to the add_raw_subroutine method '''
        module = ModuleGen(name="test")
        invalid_type = "string"
        with pytest.raises(Exception):
            module.add_raw_subroutine(invalid_type)


class TestAllocate:
    ''' pytest tests for an allocate statement. '''
    def test_allocate_arg_str(self):
        '''check that an allocate gets created succesfully with content being
        a string.'''
        module = ModuleGen(name="testmodule")
        content = "hello"
        allocate = AllocateGen(module, content)
        module.add(allocate)
        lines = str(module.root).splitlines()
        assert "ALLOCATE (" + content + ")" in lines[3]

    def test_allocate_arg_list(self):
        '''check that an allocate gets created succesfully with content being
        a list.'''
        module = ModuleGen(name="testmodule")
        content = ["hello", "how", "are", "you"]
        content_str = ""
        for idx, name in enumerate(content):
            content_str += name
            if idx+1 < len(content):
                content_str += ", "
        allocate = AllocateGen(module, content)
        module.add(allocate)
        lines = str(module.root).splitlines()
        assert "ALLOCATE (" + content_str + ")" in lines[3]

    def test_allocate_incorrect_arg_type(self):
        '''check that an allocate raises an error if an unknown type is
        passed.'''
        module = ModuleGen(name="testmodule")
        content = 3
        with pytest.raises(RuntimeError):
            _ = AllocateGen(module, content)


class TestDeallocate:
    ''' pytest tests for a deallocate statement. '''
    def test_deallocate_arg_str(self):
        '''check that a deallocate gets created succesfully with content
        being a str.'''
        module = ModuleGen(name="testmodule")
        content = "goodbye"
        deallocate = DeallocateGen(module, content)
        module.add(deallocate)
        lines = str(module.root).splitlines()
        assert "DEALLOCATE (" + content + ")" in lines[3]

    def test_deallocate_arg_list(self):
        '''check that a deallocate gets created succesfully with content
        being a list.'''
        module = ModuleGen(name="testmodule")
        content = ["and", "now", "the", "end", "is", "near"]
        content_str = ""
        for idx, name in enumerate(content):
            content_str += name
            if idx+1 < len(content):
                content_str += ", "
        deallocate = DeallocateGen(module, content)
        module.add(deallocate)
        lines = str(module.root).splitlines()
        assert "DEALLOCATE (" + content_str + ")" in lines[3]

    def test_deallocate_incorrect_arg_type(self):
        '''check that a deallocate raises an error if an unknown type is
        passed.'''
        module = ModuleGen(name="testmodule")
        content = 3
        with pytest.raises(RuntimeError):
            _ = DeallocateGen(module, content)


class TestImplicitNone():
    ''' f2pygen:ImplicitNoneGen() tests '''

    # module tests
    def test_in_a_module(self):
        ''' test that implicit none can be added to a module in the
        correct location'''
        module = ModuleGen(name="testmodule", implicitnone=False)
        module.add(ImplicitNoneGen(module))
        in_idx = line_number(module.root, "IMPLICIT NONE")
        cont_idx = line_number(module.root, "CONTAINS")
        assert in_idx > -1, "IMPLICIT NONE not found"
        assert cont_idx > -1, "CONTAINS not found"
        assert cont_idx - in_idx == 1, "CONTAINS is not on the line after" +\
            " IMPLICIT NONE"

    def test_in_a_module_with_decs(self):
        ''' test that implicit none is added before any declaration
        statements in a module when auto (the default) is used for
        insertion '''
        module = ModuleGen(name="testmodule", implicitnone=False)
        module.add(DeclGen(module, datatype="integer",
                           entity_decls=["var1"]))
        module.add(TypeDeclGen(module, datatype="my_type",
                               entity_decls=["type1"]))
        module.add(ImplicitNoneGen(module))
        in_idx = line_number(module.root, "IMPLICIT NONE")
        assert in_idx == 1

    def test_in_a_module_with_use_and_decs(self):
        ''' test that implicit none is added after any use statements
        and before any declarations in a module when auto (the
        default) is used for insertion'''
        module = ModuleGen(name="testmodule", implicitnone=False)
        module.add(DeclGen(module, datatype="integer",
                           entity_decls=["var1"]))
        module.add(TypeDeclGen(module, datatype="my_type",
                               entity_decls=["type1"]))
        module.add(UseGen(module, "fred"))
        module.add(ImplicitNoneGen(module))
        in_idx = line_number(module.root, "IMPLICIT NONE")
        assert in_idx == 2

    def test_in_a_module_with_use_and_decs_and_comments(self):
        ''' test that implicit none is added after any use statements
        and before any declarations in a module in the presence of
        comments when auto (the default) is used for insertion'''
        module = ModuleGen(name="testmodule", implicitnone=False)
        module.add(DeclGen(module, datatype="integer",
                           entity_decls=["var1"]))
        module.add(TypeDeclGen(module, datatype="my_type",
                               entity_decls=["type1"]))
        module.add(UseGen(module, "fred"))
        for idx in [0, 1, 2, 3]:
            module.add(CommentGen(module, " hello "+str(idx)),
                       position=["before_index", 2*idx])
        module.add(ImplicitNoneGen(module))
        in_idx = line_number(module.root, "IMPLICIT NONE")
        assert in_idx == 3

    def test_in_a_module_already_exists(self):
        ''' test that implicit none is not added to a module when one
        already exists'''
        module = ModuleGen(name="testmodule", implicitnone=True)
        module.add(ImplicitNoneGen(module))
        count = count_lines(module.root, "IMPLICIT NONE")
        print str(module.root)
        assert count == 1, \
            "There should only be one instance of IMPLICIT NONE"

    def test_in_a_subroutine(self):
        ''' test that implicit none can be added to a subroutine '''
        module = ModuleGen(name="testmodule")
        subroutine = SubroutineGen(module, name="testsubroutine")
        module.add(subroutine)
        subroutine.add(ImplicitNoneGen(subroutine))
        assert 'IMPLICIT NONE' in str(subroutine.root)

    def test_in_a_subroutine_with_decs(self):
        ''' test that implicit none is added before any declaration
        statements in a subroutine when auto (the default) is used for
        insertion '''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine")
        module.add(sub)
        sub.add(DeclGen(sub, datatype="integer",
                        entity_decls=["var1"]))
        sub.add(TypeDeclGen(sub, datatype="my_type",
                            entity_decls=["type1"]))
        sub.add(ImplicitNoneGen(module))
        in_idx = line_number(sub.root, "IMPLICIT NONE")
        assert in_idx == 1

    def test_in_a_subroutine_with_use_and_decs(self):
        ''' test that implicit none is added after any use statements
        and before any declarations in a subroutine when auto (the
        default) is used for insertion'''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine")
        module.add(sub)
        sub.add(DeclGen(sub, datatype="integer",
                        entity_decls=["var1"]))
        sub.add(TypeDeclGen(sub, datatype="my_type",
                            entity_decls=["type1"]))
        sub.add(UseGen(sub, "fred"))
        sub.add(ImplicitNoneGen(sub))
        in_idx = line_number(sub.root, "IMPLICIT NONE")
        assert in_idx == 2

    def test_in_a_subroutine_with_use_and_decs_and_comments(self):
        ''' test that implicit none is added after any use statements
        and before any declarations in a subroutine in the presence of
        comments when auto (the default) is used for insertion'''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine")
        module.add(sub)
        sub.add(DeclGen(sub, datatype="integer",
                        entity_decls=["var1"]))
        sub.add(TypeDeclGen(sub, datatype="my_type",
                            entity_decls=["type1"]))
        sub.add(UseGen(sub, "fred"))
        for idx in [0, 1, 2, 3]:
            sub.add(CommentGen(sub, " hello "+str(idx)),
                    position=["before_index", 2*idx])
        sub.add(ImplicitNoneGen(sub))
        in_idx = line_number(sub.root, "IMPLICIT NONE")
        assert in_idx == 3

    def test_in_a_subroutine_already_exists(self):
        ''' test that implicit none is not added to a subroutine when
        one already exists'''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine", implicitnone=True)
        module.add(sub)
        sub.add(ImplicitNoneGen(sub))
        count = count_lines(sub.root, "IMPLICIT NONE")
        assert count == 1, \
            "There should only be one instance of IMPLICIT NONE"

    def test_exception_if_wrong_parent(self):
        ''' test that an exception is thrown if implicit none is added
        and the parent is not a module or a subroutine '''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine")
        module.add(sub)
        do = DoGen(sub, "i", "1", "10")
        sub.add(do)
        with pytest.raises(Exception):
            do.add(ImplicitNoneGen(do))


class TestSubroutineGen():
    ''' f2pygen:SubroutineGen() tests '''

    def test_implicit_none_false(self):
        ''' test that implicit none is not added to the subroutine if
        not requested '''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine", implicitnone=False)
        module.add(sub)
        count = count_lines(sub.root, "IMPLICIT NONE")
        assert count == 0, "IMPLICIT NONE SHOULD NOT EXIST"

    def test_implicit_none_true(self):
        ''' test that implicit none is added to the subroutine if
        requested '''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine", implicitnone=True)
        module.add(sub)
        count = count_lines(sub.root, "IMPLICIT NONE")
        assert count == 1, "IMPLICIT NONE SHOULD EXIST"

    def test_implicit_none_default(self):
        ''' test that implicit none is not added to the subroutine by
        default '''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine")
        module.add(sub)
        count = count_lines(sub.root, "IMPLICIT NONE")
        assert count == 0, "IMPLICIT NONE SHOULD NOT EXIST BY DEFAULT"

    def test_args(self):
        ''' Test that the args property works as expected '''
        module = ModuleGen(name="testmodule")
        sub = SubroutineGen(module, name="testsubroutine",
                            args=["arg1", "arg2"])
        my_args = sub.args
        assert len(my_args) == 2


def test_directive_wrong_type():
    ''' Check that we raise an error if we request a Directive of
    unrecognised type '''
    from psyGen import Node
    parent = Node()
    with pytest.raises(RuntimeError) as err:
        _ = DirectiveGen(parent,
                         "some_dir_type", "begin", "do",
                         "schedule(static)")
    assert "unsupported directive language" in str(err)


def test_ompdirective_wrong():
    ''' Check that we raise an error if we request an OMP Directive of
    unrecognised type '''
    from psyGen import Node
    parent = Node()
    with pytest.raises(RuntimeError) as err:
        _ = DirectiveGen(parent,
                         "omp", "begin", "dosomething",
                         "schedule(static)")
    assert "unrecognised directive type" in str(err)


def test_ompdirective_wrong_posn():
    ''' Check that we raise an error if we request an OMP Directive with
    an invalid position '''
    from psyGen import Node
    parent = Node()
    with pytest.raises(RuntimeError) as err:
        _ = DirectiveGen(parent,
                         "omp", "start", "do",
                         "schedule(static)")
    assert "unrecognised position 'start'" in str(err)


def test_ompdirective_type():
    ''' Check that we can query the type of an OMP Directive '''
    from psyGen import Node
    parent = Node()
    dirgen = DirectiveGen(parent,
                          "omp", "begin", "do",
                          "schedule(static)")
    ompdir = dirgen.root
    assert ompdir.type == "do"


def test_basegen_add_auto():
    ''' Check that attempting to call add on BaseGen raises an error if
    position is "auto"'''
    from psyGen import Node
    from f2pygen import BaseGen
    parent = Node()
    bgen = BaseGen(parent, parent)
    obj = Node()
    with pytest.raises(Exception) as err:
        bgen.add(obj, position=['auto'])
    assert "auto option must be implemented by the sub" in str(err)


def test_basegen_add_invalid_posn():
    '''Check that attempting to call add on BaseGen with an invalid
    position argument raises an error'''
    from psyGen import Node
    from f2pygen import BaseGen
    parent = Node()
    bgen = BaseGen(parent, parent)
    obj = Node()
    with pytest.raises(Exception) as err:
        bgen.add(obj, position=['wrong'])
    assert "supported positions are ['append', 'first'" in str(err)


def test_basegen_append():
    '''Check that we can append an object to the tree'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sub.add(DeclGen(sub, datatype="integer",
                    entity_decls=["var1"]))
    sub.add(CommentGen(sub, " hello"), position=["append"])
    cindex = line_number(sub.root, "hello")
    assert cindex == 3


def test_basegen_first():
    '''Check that we can insert an object as the first child'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sub.add(DeclGen(sub, datatype="integer",
                    entity_decls=["var1"]))
    sub.add(CommentGen(sub, " hello"), position=["first"])
    cindex = line_number(sub.root, "hello")
    assert cindex == 1


def test_basegen_after_index():
    '''Check that we can insert an object using "after_index"'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sub.add(DeclGen(sub, datatype="integer",
                    entity_decls=["var1"]))
    sub.add(DeclGen(sub, datatype="integer",
                    entity_decls=["var2"]))
    sub.add(CommentGen(sub, " hello"), position=["after_index", 1])
    # The code checked by line_number() *includes* the SUBROUTINE
    # statement (which is obviously not a child of the SubroutineGen
    # object) and therefore the index it returns is 1 greater than we
    # might expect.
    assert line_number(sub.root, "hello") == 3


def test_basegen_before_error():
    '''Check that we raise an error when attempting to insert an object
    before another object that is not present in the tree'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sub.add(DeclGen(sub, datatype="integer",
                    entity_decls=["var1"]))
    sub.add(DeclGen(sub, datatype="integer",
                    entity_decls=["var2"]))
    # Create an object but do not add it as a child of sub
    dgen = DeclGen(sub, datatype="real",
                   entity_decls=["rvar1"])
    # Try to add an object before the orphan dgen
    with pytest.raises(RuntimeError) as err:
        sub.add(CommentGen(sub, " hello"), position=["before", dgen])
    assert "Failed to find supplied object" in str(err)


def test_basegen_last_declaration_no_vars():
    '''Check that we raise an error when requesting the position of the
    last variable declaration if we don't have any variables'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    # Request the position of the last variable declaration
    # even though we haven't got any
    with pytest.raises(RuntimeError) as err:
        sub.last_declaration()
    assert "no variable declarations found" in str(err)

    
def test_basegen_start_parent_loop_dbg(capsys):
    '''Check the debug option to the start_parent_loop method'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    loop = DoGen(sub, "it", "1", "10")
    sub.add(loop)
    call = CallGen(loop, "testcall")
    loop.add(call)
    call.start_parent_loop(debug=True)
    out, err = capsys.readouterr()
    print out
    expected = ("Parent is a do loop so moving to the parent\n"
                "The type of the current node is now <class "
                "'fparser.block_statements.Do'>\n"
                "The current node is a do loop\n"
                "The type of parent is <class "
                "'fparser.block_statements.Subroutine'>\n"
                "Finding the loops position in its parent ...\n"
                "The loop's index is  0\n")
    assert expected in out

    
def test_basegen_start_parent_loop_not_first_child_dbg(capsys):
    '''Check the debug option to the start_parent_loop method when the loop
    is not the first child of the subroutine'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    call0 = CallGen(sub, "testcall")
    sub.add(call0)
    loop = DoGen(sub, "it", "1", "10")
    sub.add(loop)
    call = CallGen(loop, "testcall")
    loop.add(call)
    call.start_parent_loop(debug=True)
    out, err = capsys.readouterr()
    print out
    expected = ("Parent is a do loop so moving to the parent\n"
                "The type of the current node is now <class "
                "'fparser.block_statements.Do'>\n"
                "The current node is a do loop\n"
                "The type of parent is <class "
                "'fparser.block_statements.Subroutine'>\n"
                "Finding the loops position in its parent ...\n"
                "The loop's index is  1\n")
    assert expected in out


def test_basegen_start_parent_loop_omp_begin_dbg(capsys):
    '''Check the debug option to the start_parent_loop method when we have
    an OpenMP begin directive'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    dgen = DirectiveGen(sub, "omp", "begin", "do", "schedule(static)")
    sub.add(dgen)
    loop = DoGen(sub, "it", "1", "10")
    sub.add(loop)
    call = CallGen(loop, "testcall")
    loop.add(call)
    call.start_parent_loop(debug=True)
    out, err = capsys.readouterr()
    print out
    expected = ("Parent is a do loop so moving to the parent\n"
                "The type of the current node is now <class "
                "'fparser.block_statements.Do'>\n"
                "The current node is a do loop\n"
                "The type of parent is <class "
                "'fparser.block_statements.Subroutine'>\n"
                "Finding the loops position in its parent ...\n"
                "The loop's index is  1\n"
                "The type of the object at the index is <class "
                "'fparser.block_statements.Do'>\n"
                "If preceding node is a directive then move back one\n"
                "preceding node is a directive so find out what type ...\n")
    assert expected in out


def test_basegen_start_parent_loop_omp_end_dbg(capsys):
    '''Check the debug option to the start_parent_loop method when we have
    an OpenMP end directive'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    dgen = DirectiveGen(sub, "omp", "end", "do", "")
    sub.add(dgen)
    loop = DoGen(sub, "it", "1", "10")
    sub.add(loop)
    call = CallGen(loop, "testcall")
    loop.add(call)
    call.start_parent_loop(debug=True)
    out, err = capsys.readouterr()
    print out
    expected = ("Parent is a do loop so moving to the parent\n"
                "The type of the current node is now <class "
                "'fparser.block_statements.Do'>\n"
                "The current node is a do loop\n"
                "The type of parent is <class "
                "'fparser.block_statements.Subroutine'>\n"
                "Finding the loops position in its parent ...\n"
                "The loop's index is  1\n"
                "The type of the object at the index is <class "
                "'fparser.block_statements.Do'>\n"
                "If preceding node is a directive then move back one\n"
                "preceding node is a directive so find out what type ...\n")

    assert expected in out


@pytest.mark.xfail(reason="fparser Call object has no member named content")
def test_basegen_start_parent_loop_no_loop_dbg(capsys):
    '''Check the debug option to the start_parent_loop method when we have
    no loop'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    dgen = DirectiveGen(sub, "omp", "end", "do", "")
    sub.add(dgen)
    call = CallGen(sub, name="testcall", args=["a", "b"])
    sub.add(call)
    call.start_parent_loop(debug=True)
    out, err = capsys.readouterr()
    print out
    expected = (
        "The type of the current node is now <class 'fparser.statements."
        "Call'>\n"
        "The type of the current node is not a do loop\n"
        "Assume the do loop will be appended as a child and find the last "
        "child's index\n")
    assert expected in out


def test_progunitgen_multiple_generic_use():
    '''Check that we correctly handle the case where duplicate use statements
    are added'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sub.add(UseGen(sub, name="fred"))
    sub.add(UseGen(sub, name="fred"))
    assert count_lines(sub.root, "USE fred") == 1


def test_progunitgen_multiple_use1():
    '''Check that we correctly handle the case where duplicate use statements
    are added but one is specific'''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sub.add(UseGen(sub, name="fred"))
    sub.add(UseGen(sub, name="fred", only=True, funcnames=["astaire"]))
    assert count_lines(sub.root, "USE fred") == 1


def test_progunitgen_multiple_use2():
    '''Check that we correctly handle the case where the same module
    appears in two use statements but, because the first use is
    specific, the second, generic use is included.

    '''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sub.add(UseGen(sub, name="fred", only=True, funcnames=["astaire"]))
    sub.add(UseGen(sub, name="fred"))
    assert count_lines(sub.root, "USE fred") == 2


def test_adduse_empty_only():
    ''' Test that the adduse module method works correctly when we specify
    that we want it to be specific but then don't provide a list of
    entities for the only qualifier '''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    from f2pygen import adduse
    # Add a use statement with only=True but an empty list of entities
    adduse("fred", sub.root, only=True, funcnames=[])
    assert count_lines(sub.root, "USE fred") == 1
    assert count_lines(sub.root, "USE fred, only") == 0


def test_adduse():
    ''' Test that the adduse module method works correctly when we use a
    call object as our starting point '''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    call = CallGen(sub, name="testcall", args=["a", "b"])
    sub.add(call)
    from f2pygen import adduse
    adduse("fred", call.root, only=True, funcnames=["astaire"])
    gen = str(sub.root)
    expected = ("    SUBROUTINE testsubroutine()\n"
                "      USE fred, ONLY: astaire\n")
    assert expected in gen


def test_declgen_wrong_type():
    ''' Check that we raise an appropriate error if we attempt to create
    a DeclGen for an unsupported type '''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    with pytest.raises(RuntimeError) as err:
        dgen = DeclGen(sub, datatype="complex",
                       entity_decls=["rvar1"])
    assert "Only integer and real are currently supported" in str(err)


def test_typedeclgen_names():
    ''' Check that the names method of TypeDeclGen works as expected '''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    dgen = TypeDeclGen(sub, datatype="my_type",
                       entity_decls=["type1"])
    sub.add(dgen)
    names = dgen.names
    assert len(names) == 1
    assert names[0] == "type1"


@pytest.mark.xfail(reason="No way to add body of DEFAULT clause")
def test_selectiongen():
    ''' Check that SelectionGen works as expected '''
    from f2pygen import SelectionGen, AssignGen
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sgen = SelectionGen(sub, expr="my_var")
    sub.add(sgen)
    agen = AssignGen(sgen, lhs="happy", rhs=".TRUE.")
    sgen.addcase("1", [agen])
    # TODO how do we specify what happens in the default case?
    sgen.adddefault()
    gen = str(sub.root)
    print gen
    expected = ("SELECT CASE ( my_var )\n"
                "CASE ( 1 )\n"
                "        happy = .TRUE.\n"
                "CASE DEFAULT\n"
                "      END SELECT")
    assert expected in gen
    assert False


@pytest.mark.xfail(reason="Adding a CASE to a SELECT TYPE does not work")
def test_typeselectiongen():
    ''' Check that SelectionGen works as expected for a type '''
    from f2pygen import SelectionGen, AssignGen
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsubroutine")
    module.add(sub)
    sgen = SelectionGen(sub, expr="my_var=>another_var", typeselect=True)
    sub.add(sgen)
    agen = AssignGen(sgen, lhs="happy", rhs=".TRUE.")
    sgen.addcase("fspace", [agen])
    sgen.adddefault()
    gen = str(sub.root)
    print gen
    assert "SELECT TYPE ( my_var=>another_var )" in gen
    assert "TYPE IS ( fspace )" in gen


def test_modulegen_add_wrong_parent():
    ''' Check that attempting to add an object to a ModuleGen fails
    if the object's parent is not that ModuleGen '''
    module = ModuleGen(name="testmodule")
    module_wrong = ModuleGen(name="another_module")
    sub = SubroutineGen(module_wrong, name="testsubroutine")
    with pytest.raises(Exception) as err:
        module.add(sub)
    assert "The requested parent is" in str(err)


def test_do_loop_with_increment():
    ''' Test that we correctly generate code for a do loop with
    non-unit increment '''
    module = ModuleGen(name="testmodule")
    sub = SubroutineGen(module, name="testsub")
    module.add(sub)
    do = DoGen(sub, "it", "1", "10", step="2")
    sub.add(do)
    count = count_lines(sub.root, "DO it=1,10,2")
    assert count == 1
