# About

This is a fairly minimal Vagrantfile and associated bootstrap scripts for
setting up a GCC-based build environment for
[TrustedFirmware-M](https://www.trustedfirmware.org).

Note that by default Vagrant shares `/vagrant` in the virtual machine with the
host. You can use this directory to copy binaries from inside the vagrant
machine out to the host for e.g. programming via USB.

# Howto

## Setting up the Vagrant virtual machine

First, you need to install Vagrant by following https://www.vagrantup.com/docs/installation.

To prepare, start and log on to the virtual machine:
```
$ cd vagrant
$ vagrant up
$ vagrant ssh
```
The initial fetching and setup will take some time, but this will only happen once when you
start the virtual machine for the first time.

Now you can follow [the main README](../README.md) for mbed-os-tf-m-regression-tests to fetch and
build the TF-M regression tests and PSA compliance tests for supported targets in the virtual
machine.

## Exiting and shutting down the virtual machine

To log out of the virtual machine, press <kbd>Ctrl</kbd> + <kbd>D</kbd>. This takes your terminal's
prompt back to your host machine, but the virtual machine is still running in the background.

To shut down the virtual machine:
```
vagrant halt
```

## Removing the virtual machine

To completely remove the virtual machine:
```
vagrant destroy
```
This removes any files in the virtual machine too.
