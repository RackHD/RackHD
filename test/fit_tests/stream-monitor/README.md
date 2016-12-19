# observer plugin for nose

To run right now:
./mkenv.sh
source myenv_fit
nosetests -v


Note, if you want to be able to work with the code "live" (rather 
than running nosetest on the working), do a
python setup.py develop

This will allow you to do stuff like:
python
>>> import sm_plugin

and so on. The 'develop' mode sets stuff up so that you work on the
code and it is instantly reflected in the environment rather than
having to reinstall it over and over again.



