import os
import re
import shutil
import logging
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED
from string import Template

import PyInstaller.__main__


RUN_SCRIPT = 'run.py'
RELEASES_PATH = 'releases'
BUILD_VERSION_TEMPLATE_PATH = 'build_version_template.txt'
SETUP_SCRIPT_TEMPLATE_PATH = 'setup_script_template.nsi'
ICON_PATH = 'resources/icon/icon.f0.ico'
RELEASE_NAME = 'RGBHardwareMonitor'
VERSION_TEMPLATE = '{version_major}.{version_minor}.{version_build}.{version_revision}'
PORTABLE_RELEASE_NAME_TEMPLATE = '{release_name}-{version}-portable.zip'
SETUP_RELEASE_NAME_TEMPLATE = '{release_name}-{version}-setup.exe'

MAKENSIS_PATH = r'C:\Program Files (x86)\NSIS\makensis.exe'


logger = logging.getLogger(__name__)


def abort(msg=None):
    if msg:
        logger.info(msg)
    logger.info('Build process aborted')
    exit(1)


def yes_no_prompt(msg):
    return input(f'{msg} [y/N]: ').lower() in ('y', 'yes')


def run_process(args, **kwargs):
    if isinstance(args, str):
        args = args.split(' ')
    run_kwargs = dict(capture_output=True, check=True, text=True)
    run_kwargs.update(kwargs)
    return subprocess.run(args, **run_kwargs)


def combined_std_out_err(process_result):
    return process_result.stdout + process_result.stderr.strip()


class TemplateFile:
    def __init__(self, template_path):
        with open(template_path, mode='r', encoding='utf8') as fp:
            self.template = Template(fp.read())

    def format(self, *args, **kwargs):
        return self.template.safe_substitute(*args, **kwargs)

    def write(self, output_path, *args, **kwargs):
        with open(output_path, mode='w', encoding='utf8') as fp:
            fp.write(self.format(*args, **kwargs))


def copy_asset(src, dest=None):
    global build_dist_path
    if dest is None:
        dest = src
    dest = os.path.join(build_dist_path, dest)
    if os.path.exists(dest):
        logger.debug(f'Removing previous existing asset "{dest}"')
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        else:
            os.remove(dest)
    logger.info(f'Copying asset "{src}" to "{dest}"')
    if os.path.isdir(src):
        shutil.copytree(src, dest)
    else:
        shutil.copyfile(src, dest)


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def zip_dir(zip_path, dir_path):
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, arcname=remove_prefix(file_path, dir_path))


def generate_setup_files_instructions(base_path, is_uninstall=False):
    prefix = "$INSTDIR"

    def emit_dir_instr(rel_path):
        nonlocal instructions
        dest_path = os.path.join(prefix, rel_path).rstrip('\\/')
        instructions.append(f'SetOutPath "{dest_path}"' if not is_uninstall else f'RmDir "{dest_path}"')

    def emit_file_instr(file_path):
        nonlocal instructions
        abs_path = os.path.abspath(file_path)
        rel_path = remove_prefix(file_path, base_path).lstrip('\\/')
        dest_path = os.path.join(prefix, rel_path)
        instructions.append(f'File "{abs_path}"' if not is_uninstall else f'Delete "{dest_path}"')

    instructions = []
    for abs_root, dirs, files in os.walk(base_path, topdown=not is_uninstall):
        rel_root = remove_prefix(abs_root, base_path).lstrip('\\/')
        if not is_uninstall:
            emit_dir_instr(rel_root)
        for file in files:
            emit_file_instr(os.path.join(abs_root, file))
        if is_uninstall and rel_root:
            emit_dir_instr(rel_root)
    return '\n'.join(instructions)


#
# ----- RELEASE BUILD START ----- #
#


# -- Check git status is clean

logger.info('Checking git status')
git_status = run_process('git status -s')
if git_status.stdout.strip():
    logger.warning(f'Git status unclean:\n{combined_std_out_err(git_status)}')
    if not yes_no_prompt('There are uncommitted/untracked files. Continue building?'):
        abort()


# -- Create version number from tags/commit

logger.info('Creating release version number')
git_describe = run_process('git describe --tags')
version_match = re.match(r'v(\d+)\.(\d+)\.(\d+)-(\d+)-(.+)\b', git_describe.stdout.strip(), flags=re.I)
if not version_match:
    abort(f'Couldn\'t extract version from git describe. Output was:\n{combined_std_out_err(git_describe)}')
version_major = version_match.group(1)
version_minor = version_match.group(2)
version_build = version_match.group(3)
version_revision = version_match.group(4)
version_commit = version_match.group(5)
version = VERSION_TEMPLATE.format(
    version_major=version_major,
    version_minor=version_minor,
    version_build=version_build,
    version_revision=version_revision,
    version_commit=version_commit
)


# -- Create release paths

logger.info('Making release paths')
release_path = os.path.join(RELEASES_PATH, version)
build_dist_path = os.path.join(release_path, 'dist')
build_work_path = os.path.join(release_path, 'temp')
build_version_path = os.path.join(release_path, 'build_version.txt')
setup_script_path = os.path.join(release_path, 'setup_script.nsi')
executable_path = os.path.join(build_dist_path, f'{RELEASE_NAME}.exe')
portable_release_path = os.path.join(release_path, PORTABLE_RELEASE_NAME_TEMPLATE.format(release_name=RELEASE_NAME,
                                                                                         version=version))
setup_release_path = os.path.join(release_path, SETUP_RELEASE_NAME_TEMPLATE.format(release_name=RELEASE_NAME,
                                                                                   version=version))
if os.path.exists(release_path):
    if not yes_no_prompt('Release directory already exists. Delete and continue building?'):
        abort()
    else:
        shutil.rmtree(release_path)
os.makedirs(release_path, exist_ok=True)


# -- Compiling build_version file

logger.info('Compiling build_version file')
build_version_template = TemplateFile(BUILD_VERSION_TEMPLATE_PATH)
build_version_namespace = dict(
    release_name=RELEASE_NAME,
    version_major=version_major,
    version_minor=version_minor,
    version_build=version_build,
    version_revision=version_revision,
    version=version,
    version_commit=version_commit,
)
build_version_template.write(build_version_path, build_version_namespace)


# -- Create dist build

logger.info('Building dist')
PyInstaller.__main__.run([
    '--clean',
    '--noconfirm',
    f'--distpath={build_dist_path}',
    f'--workpath={build_work_path}',
    '--onefile',
    '--add-data=resources;resources',
    '--hidden-import=pkg_resources',
    '--hidden-import=pkg_resources.py2_warn',
    '--windowed',
    f'--icon={ICON_PATH}',
    f'--version-file={build_version_path}',
    f'--name={RELEASE_NAME}',
    RUN_SCRIPT
])


# -- Copying additional assets

logger.info('Copying additional assets')
copy_asset('config.ini')
copy_asset('arduino')
copy_asset('LICENSE')


# -- Package portable release

logger.info('Packaging portable release')
zip_dir(portable_release_path, build_dist_path)


# -- Compiling setup_script file

logger.info('Compiling setup_script file')
setup_script_template = TemplateFile(SETUP_SCRIPT_TEMPLATE_PATH)
setup_script_install_instructions = generate_setup_files_instructions(build_dist_path)
setup_script_uninstall_instructions = generate_setup_files_instructions(build_dist_path, is_uninstall=True)
setup_script_namespace = dict(
    t_release_name=RELEASE_NAME,
    t_version=version,
    t_root_abspath=os.path.abspath('.'),
    t_setup_abspath=os.path.abspath(setup_release_path),
    t_install_instructions=setup_script_install_instructions,
    t_uninstall_instructions=setup_script_uninstall_instructions,
)
setup_script_template.write(setup_script_path, setup_script_namespace)


# -- Build setup file

logger.info('Packaging setup release')
run_process([MAKENSIS_PATH, setup_script_path])


# -- Clean up

logger.info('Cleaning up temp files')
os.remove(f'{RELEASE_NAME}.spec')
os.remove(build_version_path)
os.remove(setup_script_path)
shutil.rmtree(build_work_path)


logger.info('Done.')

#
# ----- RELEASE BUILD END ----- #
#
