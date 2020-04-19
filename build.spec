# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['run.py'],
             pathex=['E:\\Documents\\Andrea\\Projects\\RGBHardwareMonitor'],
             binaries=[],
             datas=[('resources', 'resources')],
             hiddenimports=['pkg_resources', 'pkg_resources.py2_warn'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='RGBHardwareMonitor',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False , icon='resources\\icon\\icon.f0.ico')


import shutil, os, logging

logger = logging.getLogger(__name__)

def copy_asset(src, dest=None):
    if dest is None:
        dest = src
    dest = os.path.join(DISTPATH, dest)
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

copy_asset('config.ini')
copy_asset('arduino')
copy_asset('LICENSE')
