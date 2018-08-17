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

''' Module containing tests for PSyclone Kernel Extractor '''

from __future__ import absolute_import

import os
import re
import pytest

from psyclone.parse import parse, ParseError
from psyclone.psyGen import PSyFactory, GenerationError, ExtractNode
from psyclone.configuration import ConfigFactory
from psyclone.transformations import ExtractTrans, \
    MoveTrans
from psyclone.dynamo0p3 import DynKern
from psyclone.dynamo0p3_builtins import DynBuiltIn

# constants
BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "test_files", "dynamo0p3")
# Get the root directory of this PSyclone distribution
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
# Construct the path to the default configuration file
DEFAULT_CFG_FILE = os.path.join(ROOT_PATH, "config", "psyclone.cfg")

TEST_API = "dynamo0.3"

# Our configuration objects
_CONFIG = ConfigFactory().create()
_API_CONFIG = _CONFIG.api(TEST_API)


def test_move_extract_trans():
    ''' Test MoveTrans and ExtractTrans '''
    dist_mem = False
    _, invoke_info = parse(os.path.join(BASE_PATH,
                                        "15.14.1_multi_aX_plus_Y_builtin.f90"),
                           distributed_memory=dist_mem, api=TEST_API)
    psy = PSyFactory(TEST_API, distributed_memory=dist_mem).create(invoke_info)
    invoke = psy.invokes.invoke_list[0]
    schedule = invoke.schedule
    schedule.view()

    mtrans = MoveTrans()
    etrans = ExtractTrans()

    schedule, _ = mtrans.apply(schedule.children[1],
                               schedule.children[0])
    schedule.view()

    schedule, _ = etrans.apply(schedule.children[1:3])
    schedule.view()

    fobj = schedule.children[1]
    generated_code = str(fobj.gen())
    print(generated_code)

    #assert "blah" in generated_code


def test_extract_trans():
    ''' Test ExtractTrans '''
    dist_mem = False
    _, invoke_info = parse(
        os.path.join(BASE_PATH,
                     "3_multi_invokes.f90"),
                     #"15.1.2_builtin_and_normal_kernel_invoke.f90"),
        distributed_memory=dist_mem, api=TEST_API)
    psy = PSyFactory(TEST_API, distributed_memory=dist_mem).create(invoke_info)
    for invoke in psy.invokes.invoke_list:
        print(invoke.name)

    etrans = ExtractTrans()

    for invoke in psy.invokes.invoke_list:
        ischedule = invoke.schedule
        ischedule.view()
        for child in ischedule.children:
            node = child.children[0]
            ##if isinstance(node, DynBuiltIn): # Extract all built-ins
            ##if isinstance(node, DynKern): # Extract all kernels
            if node.name == "testkern_qr_code": # Extract a specific kernel
            #if node.name == "testkern_code_w2_only": # Extract a specific kernel
                schedule, _ = etrans.apply(child)
                #schedule, _ = etrans.apply(schedule.children[1:4])
                schedule.view()
                invoke_name = invoke.name

    for node in schedule.children:
        if isinstance(node, ExtractNode):
            generated_code = str(node.gen())
            print(generated_code)

    for invoke in psy.invokes.invoke_list:
        if invoke.name == invoke_name:
            generated_code = str(invoke.gen())
            print(generated_code)

    arg_f1_write_1 = schedule.children[0].children[0].arguments.args[1]
    arg_f1_write_2 = schedule.children[3].children[0].arguments.args[1]
    assert arg_f1_write_1._depends_on(arg_f1_write_2)
