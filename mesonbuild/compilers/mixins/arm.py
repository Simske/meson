# Copyright 2012-2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Representations specific to the arm family of compilers."""

import os
import re
import typing

from ... import mesonlib
from ..compilers import clike_debug_args
from .clang import clang_color_args

if typing.TYPE_CHECKING:
    from ...environment import Environment

arm_buildtype_args = {
    'plain': [],
    'debug': ['-O0', '--debug'],
    'debugoptimized': ['-O1', '--debug'],
    'release': ['-O3', '-Otime'],
    'minsize': ['-O3', '-Ospace'],
    'custom': [],
}  # type: typing.Dict[str, typing.List[str]]

arm_optimization_args = {
    '0': ['-O0'],
    'g': ['-g'],
    '1': ['-O1'],
    '2': ['-O2'],
    '3': ['-O3'],
    's': [],
}  # type: typing.Dict[str, typing.List[str]]

armclang_buildtype_args = {
    'plain': [],
    'debug': ['-O0', '-g'],
    'debugoptimized': ['-O1', '-g'],
    'release': ['-Os'],
    'minsize': ['-Oz'],
    'custom': [],
}  # type: typing.Dict[str, typing.List[str]]

armclang_optimization_args = {
    '0': ['-O0'],
    'g': ['-g'],
    '1': ['-O1'],
    '2': ['-O2'],
    '3': ['-O3'],
    's': ['-Os']
}  # type: typing.Dict[str, typing.List[str]]


class ArmCompiler:
    # Functionality that is common to all ARM family compilers.
    def __init__(self):
        if not self.is_cross:
            raise mesonlib.EnvironmentException('armcc supports only cross-compilation.')
        self.id = 'arm'
        default_warn_args = []  # type: typing.List[str]
        self.warn_args = {'0': [],
                          '1': default_warn_args,
                          '2': default_warn_args + [],
                          '3': default_warn_args + []}
        # Assembly
        self.can_compile_suffixes.add('s')


    def get_pic_args(self) -> typing.List[str]:
        # FIXME: Add /ropi, /rwpi, /fpic etc. qualifiers to --apcs
        return []

    def get_buildtype_args(self, buildtype: str) -> typing.List[str]:
        return arm_buildtype_args[buildtype]

    # Override CCompiler.get_always_args
    def get_always_args(self) -> typing.List[str]:
        return []

    # Override CCompiler.get_dependency_gen_args
    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> typing.List[str]:
        return []

    def get_pch_use_args(self, pch_dir: str, header: str) -> typing.List[str]:
        # FIXME: Add required arguments
        # NOTE from armcc user guide:
        # "Support for Precompiled Header (PCH) files is deprecated from ARM Compiler 5.05
        # onwards on all platforms. Note that ARM Compiler on Windows 8 never supported
        # PCH files."
        return []

    def get_pch_suffix(self) -> str:
        # NOTE from armcc user guide:
        # "Support for Precompiled Header (PCH) files is deprecated from ARM Compiler 5.05
        # onwards on all platforms. Note that ARM Compiler on Windows 8 never supported
        # PCH files."
        return 'pch'

    def thread_flags(self, env: 'Environment') -> typing.List[str]:
        return []

    def get_coverage_args(self) -> typing.List[str]:
        return []

    def get_optimization_args(self, optimization_level: str) -> typing.List[str]:
        return arm_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> typing.List[str]:
        return clike_debug_args[is_debug]

    def compute_parameters_with_absolute_paths(self, parameter_list: typing.List[str], build_dir: str) -> typing.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list


class ArmclangCompiler:
    def __init__(self):
        if not self.is_cross:
            raise mesonlib.EnvironmentException('armclang supports only cross-compilation.')
        # Check whether 'armlink' is available in path
        self.linker_exe = 'armlink'
        args = '--vsn'
        try:
            p, stdo, stderr = mesonlib.Popen_safe(self.linker_exe, args)
        except OSError as e:
            err_msg = 'Unknown linker\nRunning "{0}" gave \n"{1}"'.format(' '.join([self.linker_exe] + [args]), e)
            raise mesonlib.EnvironmentException(err_msg)
        # Verify the armlink version
        ver_str = re.search('.*Component.*', stdo)
        if ver_str:
            ver_str = ver_str.group(0)
        else:
            mesonlib.EnvironmentException('armlink version string not found')
        assert ver_str  # makes mypy happy
        # Using the regular expression from environment.search_version,
        # which is used for searching compiler version
        version_regex = r'(?<!(\d|\.))(\d{1,2}(\.\d+)+(-[a-zA-Z0-9]+)?)'
        linker_ver = re.search(version_regex, ver_str)
        if linker_ver:
            linker_ver = linker_ver.group(0)
        if not mesonlib.version_compare(self.version, '==' + linker_ver):
            raise mesonlib.EnvironmentException('armlink version does not match with compiler version')
        self.id = 'armclang'
        self.base_options = ['b_pch', 'b_lto', 'b_pgo', 'b_sanitize', 'b_coverage',
                             'b_ndebug', 'b_staticpic', 'b_colorout']
        # Assembly
        self.can_compile_suffixes.update('s')

    def get_pic_args(self) -> typing.List[str]:
        # PIC support is not enabled by default for ARM,
        # if users want to use it, they need to add the required arguments explicitly
        return []

    def get_colorout_args(self, colortype: str) -> typing.List[str]:
        return clang_color_args[colortype][:]

    def get_buildtype_args(self, buildtype: str) -> typing.List[str]:
        return armclang_buildtype_args[buildtype]

    def get_pch_suffix(self) -> str:
        return 'gch'

    def get_pch_use_args(self, pch_dir: str, header: str) -> typing.List[str]:
        # Workaround for Clang bug http://llvm.org/bugs/show_bug.cgi?id=15136
        # This flag is internal to Clang (or at least not documented on the man page)
        # so it might change semantics at any time.
        return ['-include-pch', os.path.join(pch_dir, self.get_pch_name(header))]

    # Override CCompiler.get_dependency_gen_args
    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> typing.List[str]:
        return []

    def get_optimization_args(self, optimization_level: str) -> typing.List[str]:
        return armclang_optimization_args[optimization_level]

    def get_debug_args(self, is_debug: bool) -> typing.List[str]:
        return clike_debug_args[is_debug]

    def compute_parameters_with_absolute_paths(self, parameter_list: typing.List[str], build_dir: str) -> typing.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list
