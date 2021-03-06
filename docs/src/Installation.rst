LavaVu Installation
===================


Dependencies
------------

-  OpenGL and Zlib, present on most systems, headers may need to be
   installed
-  To use with python requires python 2.7+ and NumPy, python 3.6+ is recommended
-  For video output, requires: libavcodec, libavformat, libavutil, libswscale (from FFmpeg / libav)
-  To build the python interface from source requires swig (http://www.swig.org/)


Python
------

LavaVu is in the python package index, so you can install with *pip*:

It is recommended you do this in a virtualenv (like anaconda) or create you own:

::

  pip install virtualenv

  #Create a virtual env called 'python-default' and activate it:

  virtualenv python-default
  source ~/python-default/bin/activate;

..

Now you can go ahead and install LavaVu:

::

  #In anaconda or virtualenv
  pip install lavavu

  #Or to install as a user package
  pip install --user lavavu

..

   If you don’t have pip available, you can try
   ``sudo easy_install pip`` or just install
   `Anaconda <https://www.anaconda.com/download>`__, which comes with
   pip and a whole lot of other useful packages for scientific work with
   python.

   Currently no binaries are provided and the installer needs to compile
   the library, so on Linux you may need some developer tools and
   headers first, eg: for Ubuntu:
   ``sudo apt install build-essential libgl1-mesa-dev libx11-dev zlib1g-dev``


To try it out:

::

  python
  > import lavavu
  > lv = lavavu.Viewer() #Create a viewer
  > lv.test()            #Plot some sample data
  > lv.display()         #Render an image

IPython
~~~~~~~
To use the IPython notebook integration features of LavaVu you need to install a few python packages

::

  pip install ipython jupyter


Test with IPython in Jupyter, this will open the notebook interface in a web browser window
Example notebooks can be found in the 'notebooks' directory

::

  jupyter notebook

(ctrl+c in terminal to exit)

To test in a jupyter notebook:

::

  import lavavu
  lv = lavavu.Viewer() #Create a viewer

  lv.test()            #Plot some sample data

  lv.window()          #Open an inline interactive viewer window

Remember to activate the virtual env before using at a later time:

::

  source ~/python-default/bin/activate;
  cd ~/LavaVu
  jupyter notebook

Native
------

Alternatively, clone the repository with *git* and build from source:

::

  git clone https://github.com/OKaluza/LavaVu
  cd LavaVu
  make -j4

If all goes well the viewer will be built, try running with:
./lavavu/LavaVu

Build options
~~~~~~~~~~~~~

*LIBPNG=1*

- Use libpng instead of built in routines for PNG image read/write

*TIFF=1*

- Build with TIFF image read/write support (requires libtiff)

*VIDEO=1* 

- Build with MP4 video output support (requires libavcodec,libavformat,libavutil,libswscale from ffmpeg/libav)

*CONFIG=debug* 

- Debug build

*LIBDIR=/path/to/libs* 

- Adds lib path, can be used to point to a specific libGL location to use

Python bindings
~~~~~~~~~~~~~~~

The python bindings will be built automatically using the pre-generated interface files.

To test from Python:

::

    python
    > import lavavu
    > lv = lavavu.Viewer()
    > lv.test()
    > lv.display()

To allow access from outside the install directory, add it to your python path, eg:

::

    export PYTHONPATH=${PYTHONPATH}:${HOME}/LavaVu

If **swig** is installed, the interface can be rebuilt by invoking:

::

    make swig

Google Colab
------------
Experimental support for Google Colab GPU instances is provided,
a binary build for the platform is attached to each release:

::

  #Install LavaVu
  %%bash
  wget https://github.com/OKaluza/LavaVu/releases/latest/download/lavavu-colab-gpu.tar.gz
  tar xzf lavavu-colab-gpu.tar.gz

Docker
------

A base dockerfile is provided in the repository root.

You can try it out on binder

.. image:: https://mybinder.org/badge_logo.svg
 :target: https://mybinder.org/v2/gh/OKaluza/LavaVu/1.3.3?filepath=notebooks

Windows
-------

Currently the windows build is very out of date, bringing it up to date, including building a windows version of the python interface is a work in progress.

TODO : update windows build and add binary release


