#!/usr/bin/env python
"""Common test logic for shell interactions"""

# --- Global Shell Commands ---
# :-Helper-:        format_resource, is_valid_resource, random_password
# JSON:             is_json_parse, is_json_str, from_json, to_json, save_json
# Utility:          shift_directory, change_directory, list_differences, print_command
# Process:          exit_process, fail_process, process_id, process_parent_id
# Path:             current_path, expand_path, join_path, path_exists, path_dir, path_basename, path_filename
# Directory:        list_directory, create_directory, delete_directory, copy_directory, sync_directory
# File:             read_file, write_file, delete_file, rename_file, copy_file, hash_file, file_match, backup_file
# Signal:           max_signal, handle_signal, send_signal
# SubProcess:       run_subprocess, log_subprocess

import shell_boilerplate as sh

# ------------------------ Global Test Commands ------------------------

# --- Helper Commands ---


def test_system_platform():
    """Verify the output of 'system_platform' function"""
    accepted_values = ['windows', 'linux']
    output = sh.system_platform()
    assert output in accepted_values


def test_format_resource():
    """Verify the output of 'format_resource' function"""
    mock_name = "rg-001"
    output = sh.format_resource(mock_name)
    assert output == "rg-001"


def test_is_valid_resource():
    """Verify the output of 'is_valid_resource' function"""
    mock_name = "rg-001"
    output = sh.is_valid_resource(mock_name)
    assert output is True


def test_random_password():
    """Verify the output of 'random_password' function"""
    output = sh.random_password()
    assert isinstance(output, str) is True
    assert len(output) == 16


# --- Utility Commands ---

def test_list_differences():
    """Verify the output of 'list_differences' function"""
    mock_list_a = ['a', 'b', 'c', 'd', 'e']
    mock_list_b = ['a', 'b', 'c']
    output = sh.list_differences(mock_list_a, mock_list_b)
    assert output == ['d', 'e']
    output = sh.list_differences(mock_list_b, mock_list_a)
    assert output == []


def test_process_id():
    """Verify the output of 'process_id' function"""
    output = sh.process_id()
    assert isinstance(output, int) and output > 0


def test_process_parent_id():
    """Verify the output of 'process_parent_id' function"""
    output = sh.process_parent_id()
    assert isinstance(output, int) and output > 0


def test_current_path():
    """Verify the output of 'current_path' function"""
    output = sh.current_path()
    assert isinstance(output, str) and len(output) > 0


def test_path_basename():
    """Verify the output of 'path_basename' function"""
    mock_path = "F:\\Repos\\pc-env\\powershell\\provision_python.ps1"
    output = sh.path_basename(mock_path)
    assert output == "provision_python.ps1"


def test_path_filename():
    """Verify the output of 'path_filename' function"""
    mock_path = "F:\\Repos\\pc-env\\powershell\\provision_python.ps1"
    output = sh.path_filename(mock_path)
    assert output == "provision_python"


# --- JSON Commands ---

def test_from_json():
    """Verify the output of 'from_json' function"""
    mock_json = '["foo", {"bar": ["baz", null, 1.0, 2]}]'
    output = sh.from_json(mock_json)
    assert output == ['foo', {'bar': ['baz', None, 1.0, 2]}]


def test_to_json():
    """Verify the output of 'to_json' function"""
    mock_json = ['foo', {'bar': ['baz', None, 1.0, 2]}]
    output = sh.to_json(mock_json)
    assert output == '["foo", {"bar": ["baz", null, 1.0, 2]}]'

# def test_is_json_parse():
#     """Verify the output of 'is_json_parse' function"""
#     mock_path = "F:\\Repos\\pc-env\\powershell\\provision_python.ps1"
#     output = sh.is_json_parse(mock_path)
#     assert output == "provision_python"
