import sys
from pathlib import Path

__dir__ = Path(__file__).absolute().parent
# Remove current dir from sys.path, otherwise setuptools will peek up our
# module instead of system's.
sys.path.pop(0)
from setuptools import setup

sys.path.append(".")
import sdist_upip

setup(
    name='esp32ecp5',
    py_modules=['ecp5setup','ecp5','ecp5wp','sdraw','uftpd','wifiman','gzip4k'],
    version='1.0.19',
    description='MicroPython ESP32 JTAG programmer for ECP5 FPGA',
    long_description='Full featured ECP5 FPGA programmer with native support for ULX3S boards',
    long_description_content_type="text/markdown",
    keywords='JTAG, FPGA, ECP5, WiFi, FTP, FLASH, SD',
    url='https://github.com/emard/esp32ecp5',
    author='EMARD',
    author_email='vordah@gmail.com',
    maintainer='EMARD',
    maintainer_email='vordah@gmail.com',
    license='MIT',
    cmdclass={'sdist': sdist_upip.sdist},
    project_urls={
        'Bug Reports': 'https://github.com/emard/esp32ecp5/issues',
        'Documentation': 'https://github.com/emard/esp32ecp5/blob/master/README.md',
        'Source': 'https://github.com/emard/esp32ecp5',
    },
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: Implementation :: MicroPython',
        'License :: OSI Approved :: MIT License',
    ],
)
