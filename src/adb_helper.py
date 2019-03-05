import subprocess
import sys

try:
    # This fails when the code is executed directly and not as a part of python package installation,
    # I definitely need a better way to handle this.
    from adbe.output_helper import print_error, print_error_and_exit, print_verbose
except ImportError:
    # This works when the code is executed directly.
    from output_helper import print_error, print_error_and_exit, print_verbose


_adb_prefix = 'adb'
_IGNORED_LINES = [
    'WARNING: linker: libdvm.so has text relocations. This is wasting memory and is a security risk. Please fix.'
]

# This won't be required once I deprecate Python 2.
if sys.version_info[0] >= 3:
    unicode = str


def get_adb_prefix():
    return _adb_prefix


def set_adb_prefix(adb_prefix):
    # pylint: disable=global-statement
    global _adb_prefix
    _adb_prefix = adb_prefix


def get_adb_shell_property(property_name, device_serial=None):
    _, stdout, _ = execute_adb_shell_command2('getprop %s' % property_name, device_serial=device_serial)
    return stdout


def execute_adb_shell_command2(adb_cmd, piped_into_cmd=None, ignore_stderr=False, device_serial=None):
    return execute_adb_command2('shell %s' % adb_cmd, piped_into_cmd=piped_into_cmd,
                                ignore_stderr=ignore_stderr, device_serial=device_serial)


def execute_adb_command2(adb_cmd, piped_into_cmd=None, ignore_stderr=False, device_serial=None):
    adb_prefix = _adb_prefix
    if device_serial:
        adb_prefix = '%s -s %s' % (adb_prefix, device_serial)

    final_cmd = ('%s %s' % (adb_prefix, adb_cmd))
    if piped_into_cmd:
        final_cmd = '%s | %s' % (final_cmd, piped_into_cmd)

    print_verbose("Executing \"%s\"" % final_cmd)
    ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = ps1.communicate()
    return_code = ps1.returncode
    try:
        stdout_data = stdout_data.decode('utf-8')
    except UnicodeDecodeError:
        print_error('Unable to decode data as UTF-8, defaulting to printing the binary data')
    stderr_data = stderr_data.decode('utf-8')

    _check_for_more_than_one_device_error(stderr_data)
    _check_for_device_not_found_error(stderr_data)
    if not ignore_stderr and stderr_data and len(stderr_data) > 0:
        print_error(stderr_data)

    if stdout_data:
        if isinstance(stdout_data, bytes):
            print_verbose("Result is \"%s\"" % stdout_data)
            return return_code, stdout_data, stderr_data
        # str for Python 3 and unicode for Python 2
        # unicode is undefined for Python 3
        elif isinstance(stdout_data, (str, unicode)):
            output = ''
            first_line = True
            for line in stdout_data.split('\n'):
                line = line.strip()
                if not line or len(line) == 0:
                    continue
                if line in _IGNORED_LINES:
                    continue
                if first_line:
                    output += line
                    first_line = False
                else:
                    output += '\n' + line
            print_verbose("Result is \"%s\"" % output)
            return return_code, output, stderr_data
    else:
        return return_code, None, stderr_data


# Deprecated
def execute_adb_shell_command(adb_cmd, piped_into_cmd=None, ignore_stderr=False, device_serial=None):
    _, stdout, _ = execute_adb_command2(
        'shell %s' % adb_cmd, piped_into_cmd, ignore_stderr, device_serial=device_serial)
    return stdout


# Deprecated
def execute_adb_command(adb_cmd, piped_into_cmd=None, ignore_stderr=False, device_serial=None):
    adb_prefix = _adb_prefix
    if device_serial:
        adb_prefix = '%s -s %s' % (adb_prefix, device_serial)
    final_cmd = ('%s %s' % (adb_prefix, adb_cmd))
    if piped_into_cmd:
        final_cmd = '%s | %s' % (final_cmd, piped_into_cmd)

    print_verbose("Executing \"%s\"" % final_cmd)
    ps1 = subprocess.Popen(final_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data, stderr_data = ps1.communicate()
    try:
        stdout_data = stdout_data.decode('utf-8')
    except UnicodeDecodeError:
        print_error('Unable to decode data as UTF-8, defaulting to printing the binary data')
    stderr_data = stderr_data.decode('utf-8')

    _check_for_more_than_one_device_error(stderr_data)
    _check_for_device_not_found_error(stderr_data)
    if not ignore_stderr and stderr_data and len(stderr_data) > 0:
        print_error(stderr_data)

    if stdout_data:
        if isinstance(stdout_data, bytes):
            print_verbose("Result is \"%s\"" % stdout_data)
            return stdout_data
        # str for Python 3 and unicode for Python 2
        # unicode is undefined for Python 3
        elif isinstance(stdout_data, (str, unicode)):
            output = ''
            first_line = True
            for line in stdout_data.split('\n'):
                line = line.strip()
                if not line or len(line) == 0:
                    continue
                if line in _IGNORED_LINES:
                    continue
                if first_line:
                    output += line
                    first_line = False
                else:
                    output += '\n' + line
            print_verbose("Result is \"%s\"" % output)
            return output

    return None


def _check_for_more_than_one_device_error(stderr_data):
    if not stderr_data:
        return
    for line in stderr_data.split('\n'):
        line = line.strip()
        if line and len(line) > 0:
            print_verbose(line)
        if line.find('error: more than one') != -1:
            message = ''
            message += 'More than one device/emulator are connected.\n'
            message += 'Please select a device by providing the serial ID (-s parameter).\n'
            message += 'You can list all connected devices/emulators via \"devices\" subcommand.'
            print_error_and_exit(message)


def _check_for_device_not_found_error(stderr_data):
    if not stderr_data:
        return
    for line in stderr_data.split('\n'):
        line = line.strip()
        if line and len(line) > 0:
            print_verbose(line)
        if line.find('error: device') > -1 and line.find('not found') > -1:
            print_error_and_exit(line)
