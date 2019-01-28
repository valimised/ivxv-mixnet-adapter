# ivxv-mixnet-adapter
Tools to use Verificatum mixnet and IVXV together

IVXV is the next-generation internet voting software for Estonia.
Verificatum is the shuffling mixnet.

This repository contains an adapter to convert from data structures from IXVX to
Verificatum formats and vice versa. Also, it includes a runner script which
initializes Verificatum configuration and runs the shuffle.

Preparation
-----------

No libraries are included in this repository. The required libraries are
compiled as needed. For that, the following assumptions are made:

* gradle is installed
* IVXV repository is stored at `../ivxv/`

* Verificatum GMPMEE repository is stored at `../gmpmee/`. To checkout, run::

    git clone https://github.com/verificatum/verificatum-gmpmee gmpmee

* Verificatum VMGJ repository is stored at `../vmgj/`. To checkout, run::

    git clone https://github.com/verificatum/vmgj

* Verificatum VCR repository is stored at `../vcr/`. To checkout, run::

    git clone https://github.com/verificatum/vcr

* Verificatum VMN repository is stored at `../vmn/`. To checkout, run::

    git clone https://github.com/verificatum/vmn

Building
--------

The release is built using `make zip`. The release including Verificatum
libraries can be built using `make zipext`.

The releases are built into `release/ivxv-verificatum-{VERSION}-runner.zip` and
`release/ivxv-verificatum-{VERSION}-runner-with-verificatum.zip`.

Usage
-----

From the release, run `bin/mix.py -h` to see the usage information of the
adapter.  The proof is created in the working directory. To clean up the current
directory from shuffle proof, run `bin/clean`.


