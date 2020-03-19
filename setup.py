import os

import PyInstaller.__main__

PyInstaller.__main__.run([
    '--name=hotsdraft-overlay',
    '--onefile',
    '--add-binary={0}{1}portraits'.format(os.path.join('hotsdraft_overlay', 'portraits', '*.png'), os.pathsep),
    '--add-data={0}{1}.'.format(os.path.join('hotsdraft_overlay', 'data.json'), os.pathsep),
    os.path.join('hotsdraft_overlay', 'runner.py'),
])
