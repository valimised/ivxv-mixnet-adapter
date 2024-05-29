#!/bin/bash

git clone https://github.com/verificatum/verificatum-gmpmee
git clone https://github.com/verificatum/vmgj
git clone https://github.com/verificatum/vcr
git clone https://github.com/verificatum/vmn

cd verificatum-gmpmee
git checkout -q 4aafc31
cd ../vmgj
git checkout -q 8d7d412
cd ../vcr
git checkout -q af9fd82
cd ../vmn
git checkout -q bb00543
cd ..
